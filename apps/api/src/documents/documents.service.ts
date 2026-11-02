import {
  Injectable,
  NotFoundException,
  BadRequestException,
  Logger,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import { StorageService } from '../storage/storage.service.js';
import { QueryDocumentsDto } from './dto/query-documents.dto.js';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import {
  DOCUMENT_INGESTION_QUEUE,
  DOCUMENT_INGESTION_JOB,
} from '../queue/queue.constants.js';
import { FileType, DocumentStatus } from '@prisma/client';
import * as crypto from 'crypto';
import * as path from 'path';

const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25 MB

const MIME_TO_FILE_TYPE: Record<string, FileType> = {
  'application/pdf': FileType.PDF,
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
    FileType.DOCX,
  'text/plain': FileType.TXT,
};

const EXTENSION_TO_FILE_TYPE: Record<string, FileType> = {
  '.pdf': FileType.PDF,
  '.docx': FileType.DOCX,
  '.txt': FileType.TXT,
};

@Injectable()
export class DocumentsService {
  private readonly logger = new Logger(DocumentsService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly storageService: StorageService,
    @InjectQueue(DOCUMENT_INGESTION_QUEUE)
    private readonly documentQueue: Queue,
  ) {}

  /**
   * Tải tài liệu lên Object Storage và lưu Metadata vào Database
   */
  async upload(
    workspaceId: string,
    userId: string,
    file: Express.Multer.File,
  ) {
    if (!file) {
      throw new BadRequestException('Vui lòng chọn một tệp để tải lên');
    }

    if (file.size > MAX_FILE_SIZE) {
      throw new BadRequestException(
        `Kích thước tệp vượt quá giới hạn tối đa 25MB (Hiện tại: ${(file.size / (1024 * 1024)).toFixed(2)}MB)`,
      );
    }

    const fileType = this.resolveFileType(file.mimetype, file.originalname);
    if (!fileType) {
      throw new BadRequestException(
        'Định dạng tệp không được hỗ trợ. Hệ thống chỉ chấp nhận PDF, DOCX, TXT',
      );
    }

    const sanitizedOriginalName = file.originalname.replace(/[^a-zA-Z0-9._-]/g, '_');
    const fileId = crypto.randomUUID();
    const storagePath = `workspaces/${workspaceId}/documents/${Date.now()}-${fileId}-${sanitizedOriginalName}`;

    // 1. Lưu file lên Object Storage (MinIO / S3)
    await this.storageService.uploadFile(storagePath, file.buffer, file.mimetype);

    // 2. Tạo bản ghi Document trong PostgreSQL
    const document = await this.prisma.document.create({
      data: {
        workspaceId,
        createdById: userId,
        title: path.parse(file.originalname).name || 'Untitled Document',
        originalName: file.originalname,
        storagePath,
        fileType,
        fileSize: file.size,
        mimeType: file.mimetype || 'application/octet-stream',
        status: DocumentStatus.PENDING,
      },
      include: {
        createdBy: {
          select: {
            id: true,
            email: true,
            fullName: true,
          },
        },
      },
    });

    this.logger.log(
      `Document "${document.title}" (${document.id}) uploaded to workspace ${workspaceId}`,
    );

    // 3. Đưa công việc Ingestion (trích xuất, chunking, embedding) vào hàng đợi ngầm BullMQ
    try {
      await this.documentQueue.add(DOCUMENT_INGESTION_JOB, {
        documentId: document.id,
        workspaceId,
        storagePath,
        fileType,
      });
      this.logger.log(`Ingestion job queued for document: ${document.id}`);
    } catch (queueError) {
      this.logger.warn(
        `Không thể gửi tác vụ vào hàng đợi (Redis có thể chưa bật): ${(queueError as Error).message}`,
      );
    }

    return document;
  }

  /**
   * Lấy danh sách tài liệu trong Workspace có phân trang và lọc theo trạng thái
   */
  async findAll(workspaceId: string, query: QueryDocumentsDto) {
    const page = query.page ?? 1;
    const limit = query.limit ?? 20;
    const skip = (page - 1) * limit;

    const where = {
      workspaceId,
      ...(query.status ? { status: query.status } : {}),
    };

    const [total, documents] = await Promise.all([
      this.prisma.document.count({ where }),
      this.prisma.document.findMany({
        where,
        skip,
        take: limit,
        orderBy: {
          createdAt: 'desc',
        },
        include: {
          createdBy: {
            select: {
              id: true,
              email: true,
              fullName: true,
            },
          },
          _count: {
            select: {
              chunks: true,
            },
          },
        },
      }),
    ]);

    return {
      data: documents,
      meta: {
        total,
        page,
        limit,
        totalPages: Math.ceil(total / limit),
      },
    };
  }

  /**
   * Lấy chi tiết tài liệu theo ID
   */
  async findOne(workspaceId: string, documentId: string) {
    const document = await this.prisma.document.findFirst({
      where: {
        id: documentId,
        workspaceId,
      },
      include: {
        createdBy: {
          select: {
            id: true,
            email: true,
            fullName: true,
          },
        },
        _count: {
          select: {
            chunks: true,
          },
        },
      },
    });

    if (!document) {
      throw new NotFoundException('Không tìm thấy tài liệu trong Workspace này');
    }

    return document;
  }

  /**
   * Xóa tài liệu khỏi Database và Object Storage
   */
  async delete(workspaceId: string, documentId: string) {
    const document = await this.findOne(workspaceId, documentId);

    // Xóa trong database trước (Cascade tự động xóa chunks và message sources)
    await this.prisma.document.delete({
      where: { id: documentId },
    });

    // Xóa file gốc trong Object Storage
    await this.storageService.deleteFile(document.storagePath);

    this.logger.log(`Document ${documentId} deleted successfully.`);
    return { success: true };
  }

  /**
   * Lấy Stream của file gốc để download
   */
  async getFileStream(workspaceId: string, documentId: string) {
    const document = await this.findOne(workspaceId, documentId);
    const stream = await this.storageService.getFileStream(document.storagePath);

    return {
      stream,
      document,
    };
  }

  /**
   * Xác định FileType từ MIME type hoặc đuôi file
   */
  private resolveFileType(
    mimeType: string,
    fileName: string,
  ): FileType | null {
    if (MIME_TO_FILE_TYPE[mimeType]) {
      return MIME_TO_FILE_TYPE[mimeType];
    }

    const ext = path.extname(fileName).toLowerCase();
    if (EXTENSION_TO_FILE_TYPE[ext]) {
      return EXTENSION_TO_FILE_TYPE[ext];
    }

    return null;
  }
}

