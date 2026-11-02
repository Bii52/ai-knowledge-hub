import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Test, TestingModule } from '@nestjs/testing';
import { NotFoundException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ConversationsService } from './conversations.service.js';
import { PrismaService } from '../prisma/prisma.service.js';
import { SenderType } from '@prisma/client';

describe('ConversationsService', () => {
  let service: ConversationsService;
  let prisma: {
    conversation: {
      create: ReturnType<typeof vi.fn>;
      findMany: ReturnType<typeof vi.fn>;
      findFirst: ReturnType<typeof vi.fn>;
      update: ReturnType<typeof vi.fn>;
      delete: ReturnType<typeof vi.fn>;
    };
    message: {
      create: ReturnType<typeof vi.fn>;
      count: ReturnType<typeof vi.fn>;
    };
    messageSource: {
      create: ReturnType<typeof vi.fn>;
    };
    documentChunk: {
      findMany: ReturnType<typeof vi.fn>;
    };
  };

  const mockWorkspaceId = 'ws-123';
  const mockUserId = 'user-456';
  const mockConversationId = 'conv-789';

  const mockConversation = {
    id: mockConversationId,
    workspaceId: mockWorkspaceId,
    createdById: mockUserId,
    title: 'Hội thoại về RAG',
    createdAt: new Date(),
    updatedAt: new Date(),
    messages: [],
  };

  beforeEach(async () => {
    prisma = {
      conversation: {
        create: vi.fn(),
        findMany: vi.fn(),
        findFirst: vi.fn(),
        update: vi.fn(),
        delete: vi.fn(),
      },
      message: {
        create: vi.fn(),
        count: vi.fn(),
      },
      messageSource: {
        create: vi.fn(),
      },
      documentChunk: {
        findMany: vi.fn(),
      },
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        ConversationsService,
        { provide: PrismaService, useValue: prisma },
        {
          provide: ConfigService,
          useValue: {
            get: vi.fn().mockReturnValue('http://localhost:8000'),
          },
        },
      ],
    }).compile();

    service = module.get<ConversationsService>(ConversationsService);
  });

  describe('create', () => {
    it('tạo cuộc hội thoại mới trong Workspace thành công', async () => {
      prisma.conversation.create.mockResolvedValue(mockConversation);

      const result = await service.create(mockWorkspaceId, mockUserId, {
        title: 'Hội thoại về RAG',
      });

      expect(result.id).toBe(mockConversationId);
      expect(result.title).toBe('Hội thoại về RAG');
      expect(prisma.conversation.create).toHaveBeenCalledOnce();
    });
  });

  describe('findOne', () => {
    it('trả về cuộc hội thoại nếu tồn tại trong Workspace', async () => {
      prisma.conversation.findFirst.mockResolvedValue(mockConversation);

      const result = await service.findOne(mockWorkspaceId, mockConversationId);
      expect(result.id).toBe(mockConversationId);
    });

    it('báo lỗi NotFoundException nếu không tìm thấy hội thoại', async () => {
      prisma.conversation.findFirst.mockResolvedValue(null);

      await expect(
        service.findOne(mockWorkspaceId, 'invalid-conv'),
      ).rejects.toThrow(NotFoundException);
    });
  });

  describe('sendMessage', () => {
    it('lưu tin nhắn người dùng và sinh phản hồi kèm nguồn trích dẫn', async () => {
      prisma.conversation.findFirst.mockResolvedValue(mockConversation);
      prisma.message.count.mockResolvedValue(1);

      const mockUserMsg = {
        id: 'msg-user-1',
        conversationId: mockConversationId,
        senderType: SenderType.USER,
        content: 'RAG là gì?',
        createdAt: new Date(),
      };

      const mockAssistantMsg = {
        id: 'msg-ai-2',
        conversationId: mockConversationId,
        senderType: SenderType.ASSISTANT,
        content: 'RAG là Retrieval-Augmented Generation...',
        createdAt: new Date(),
      };

      prisma.message.create
        .mockResolvedValueOnce(mockUserMsg)
        .mockResolvedValueOnce(mockAssistantMsg);

      prisma.documentChunk.findMany.mockResolvedValue([
        {
          id: 'chunk-1',
          documentId: 'doc-1',
          content: 'RAG là viết tắt của Retrieval-Augmented Generation...',
          pageNumber: 3,
          document: {
            id: 'doc-1',
            title: 'Khai niem RAG',
          },
        },
      ]);

      prisma.messageSource.create.mockResolvedValue({
        id: 'source-1',
        messageId: 'msg-ai-2',
        documentId: 'doc-1',
        chunkId: 'chunk-1',
      });

      prisma.conversation.update.mockResolvedValue(mockConversation);

      const result = await service.sendMessage(
        mockWorkspaceId,
        mockConversationId,
        mockUserId,
        { content: 'RAG là gì?' },
      );

      expect(result.userMessage.id).toBe('msg-user-1');
      expect(result.assistantMessage.id).toBe('msg-ai-2');
      expect(result.assistantMessage.sources).toHaveLength(1);
      expect(result.assistantMessage.sources[0].chunkId).toBe('chunk-1');
      expect(prisma.messageSource.create).toHaveBeenCalledOnce();
    });
  });
});

