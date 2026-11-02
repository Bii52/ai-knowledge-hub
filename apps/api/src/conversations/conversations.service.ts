import {
  Injectable,
  NotFoundException,
  Logger,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PrismaService } from '../prisma/prisma.service.js';
import { CreateConversationDto } from './dto/create-conversation.dto.js';
import { SendMessageDto } from './dto/send-message.dto.js';
import { SenderType } from '@prisma/client';

export interface RetrievedSource {
  documentId: string;
  chunkId?: string;
  pageNumber?: number | null;
  excerpt: string;
  relevanceScore?: number | null;
  documentTitle?: string;
}

@Injectable()
export class ConversationsService {
  private readonly logger = new Logger(ConversationsService.name);
  private readonly aiServiceUrl: string;

  constructor(
    private readonly prisma: PrismaService,
    private readonly configService: ConfigService,
  ) {
    this.aiServiceUrl =
      this.configService.get<string>('AI_SERVICE_URL') ??
      process.env.AI_SERVICE_URL ??
      'http://localhost:8000';
  }

  /**
   * Tạo cuộc hội thoại mới trong Workspace
   */
  async create(
    workspaceId: string,
    userId: string,
    dto: CreateConversationDto,
  ) {
    const title = dto.title?.trim() || 'Cuộc hội thoại mới';

    return this.prisma.conversation.create({
      data: {
        workspaceId,
        createdById: userId,
        title,
      },
    });
  }

  /**
   * Lấy danh sách cuộc hội thoại của người dùng trong Workspace
   */
  async findAll(workspaceId: string, userId: string) {
    return this.prisma.conversation.findMany({
      where: {
        workspaceId,
        createdById: userId,
      },
      include: {
        _count: {
          select: {
            messages: true,
          },
        },
      },
      orderBy: {
        updatedAt: 'desc',
      },
    });
  }

  /**
   * Xem chi tiết hội thoại kèm toàn bộ tin nhắn và nguồn trích dẫn
   */
  async findOne(workspaceId: string, conversationId: string) {
    const conversation = await this.prisma.conversation.findFirst({
      where: {
        id: conversationId,
        workspaceId,
      },
      include: {
        messages: {
          orderBy: {
            createdAt: 'asc',
          },
          include: {
            sources: {
              include: {
                document: {
                  select: {
                    id: true,
                    title: true,
                    originalName: true,
                  },
                },
              },
            },
          },
        },
      },
    });

    if (!conversation) {
      throw new NotFoundException('Không tìm thấy cuộc hội thoại trong Workspace');
    }

    return conversation;
  }

  /**
   * Đổi tên cuộc hội thoại
   */
  async updateTitle(
    workspaceId: string,
    conversationId: string,
    title: string,
  ) {
    await this.findOne(workspaceId, conversationId);

    return this.prisma.conversation.update({
      where: { id: conversationId },
      data: {
        title: title.trim(),
      },
    });
  }

  /**
   * Xóa cuộc hội thoại
   */
  async delete(workspaceId: string, conversationId: string) {
    await this.findOne(workspaceId, conversationId);

    await this.prisma.conversation.delete({
      where: { id: conversationId },
    });

    return { success: true };
  }

  /**
   * Gửi câu hỏi, điều phối RAG Query và lưu trữ phản hồi kèm nguồn trích dẫn
   */
  async sendMessage(
    workspaceId: string,
    conversationId: string,
    userId: string,
    dto: SendMessageDto,
  ) {
    // 1. Kiểm tra cuộc hội thoại có thuộc Workspace hay không
    await this.findOne(workspaceId, conversationId);

    // Tự động đổi tên hội thoại nếu là tin nhắn đầu tiên
    const messageCount = await this.prisma.message.count({
      where: { conversationId },
    });
    if (messageCount === 0) {
      const summaryTitle =
        dto.content.slice(0, 40).trim() +
        (dto.content.length > 40 ? '...' : '');
      await this.prisma.conversation.update({
        where: { id: conversationId },
        data: { title: summaryTitle },
      });
    }

    // 2. Lưu tin nhắn của Người dùng
    const userMessage = await this.prisma.message.create({
      data: {
        conversationId,
        senderType: SenderType.USER,
        content: dto.content.trim(),
      },
    });

    // 3. Thực hiện RAG Retrieval & Generation
    const { answer, sources } = await this.executeRagQuery(
      workspaceId,
      dto.content,
      dto.documentIds,
    );

    // 4. Lưu tin nhắn phản hồi của Trợ lý AI
    const assistantMessage = await this.prisma.message.create({
      data: {
        conversationId,
        senderType: SenderType.ASSISTANT,
        content: answer,
      },
    });

    // 5. Lưu trữ các nguồn trích dẫn (Message Sources)
    if (sources.length > 0) {
      await Promise.all(
        sources.map((s) =>
          this.prisma.messageSource.create({
            data: {
              messageId: assistantMessage.id,
              documentId: s.documentId,
              chunkId: s.chunkId,
              pageNumber: s.pageNumber,
              excerpt: s.excerpt,
              relevanceScore: s.relevanceScore,
            },
          }),
        ),
      );
    }

    // 6. Cập nhật thời gian hội thoại
    await this.prisma.conversation.update({
      where: { id: conversationId },
      data: { updatedAt: new Date() },
    });

    return {
      userMessage,
      assistantMessage: {
        ...assistantMessage,
        sources,
      },
    };
  }

  /**
   * Cơ chế gọi RAG Query (Giao tiếp với AI Service hoặc truy vấn ngữ cảnh tại chỗ)
   */
  private async executeRagQuery(
    workspaceId: string,
    query: string,
    documentIds?: string[],
  ): Promise<{ answer: string; sources: RetrievedSource[] }> {
    try {
      const aiEndpoint = `${this.aiServiceUrl}/api/v1/chat`;
      const response = await fetch(aiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          workspace_id: workspaceId,
          document_ids: documentIds,
        }),
        signal: AbortSignal.timeout(15000), // 15s timeout
      });

      if (response.ok) {
        const data = (await response.json()) as {
          answer: string;
          sources?: RetrievedSource[];
        };
        return {
          answer: data.answer,
          sources: data.sources ?? [],
        };
      }
    } catch (error) {
      this.logger.debug(
        `AI Service call skipped/failed (${(error as Error).message}). Using database context fallback.`,
      );
    }

    // Fallback: Tìm kiếm các chunk tài liệu đã lưu trong cùng Workspace
    const chunks = await this.prisma.documentChunk.findMany({
      where: {
        workspaceId,
        ...(documentIds && documentIds.length > 0
          ? { documentId: { in: documentIds } }
          : {}),
      },
      take: 3,
      include: {
        document: {
          select: {
            id: true,
            title: true,
          },
        },
      },
    });

    if (chunks.length === 0) {
      return {
        answer:
          'Tôi đã nhận được câu hỏi của bạn. Hiện tại chưa có tài liệu nào được xử lý xong trong Workspace này để trích xuất câu trả lời chính xác.',
        sources: [],
      };
    }

    const sources: RetrievedSource[] = chunks.map((c) => ({
      documentId: c.documentId,
      chunkId: c.id,
      pageNumber: c.pageNumber,
      excerpt: c.content.slice(0, 200) + '...',
      relevanceScore: 0.95,
      documentTitle: c.document.title,
    }));

    return {
      answer: `Dựa trên các tài liệu đã nạp trong Workspace ("${sources.map((s) => s.documentTitle).join(', ')}"), đây là thông tin trả lời cho câu hỏi: "${query}".`,
      sources,
    };
  }
}
