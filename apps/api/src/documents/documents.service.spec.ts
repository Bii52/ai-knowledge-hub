import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Test, TestingModule } from '@nestjs/testing';
import { BadRequestException, NotFoundException } from '@nestjs/common';
import { getQueueToken } from '@nestjs/bullmq';
import { DocumentsService } from './documents.service.js';
import { PrismaService } from '../prisma/prisma.service.js';
import { StorageService } from '../storage/storage.service.js';
import { DOCUMENT_INGESTION_QUEUE } from '../queue/queue.constants.js';
import { FileType, DocumentStatus } from '@prisma/client';

describe('DocumentsService', () => {
  let service: DocumentsService;
  let queue: {
    add: ReturnType<typeof vi.fn>;
  };
  let prisma: {
    document: {
      create: ReturnType<typeof vi.fn>;
      findMany: ReturnType<typeof vi.fn>;
      findFirst: ReturnType<typeof vi.fn>;
      count: ReturnType<typeof vi.fn>;
      delete: ReturnType<typeof vi.fn>;
    };
  };
  let storage: {
    uploadFile: ReturnType<typeof vi.fn>;
    deleteFile: ReturnType<typeof vi.fn>;
    getFileStream: ReturnType<typeof vi.fn>;
  };

  const mockWorkspaceId = 'ws-123';
  const mockUserId = 'user-456';
  const mockDocumentId = 'doc-789';

  const mockDoc = {
    id: mockDocumentId,
    workspaceId: mockWorkspaceId,
    createdById: mockUserId,
    title: 'Test Document',
    originalName: 'test.pdf',
    storagePath: 'workspaces/ws-123/documents/123-test.pdf',
    fileType: FileType.PDF,
    fileSize: 1024,
    mimeType: 'application/pdf',
    status: DocumentStatus.PENDING,
    errorMessage: null,
    createdAt: new Date(),
    updatedAt: new Date(),
  };

  beforeEach(async () => {
    prisma = {
      document: {
        create: vi.fn(),
        findMany: vi.fn(),
        findFirst: vi.fn(),
        count: vi.fn(),
        delete: vi.fn(),
      },
    };

    storage = {
      uploadFile: vi.fn().mockResolvedValue('storage-key'),
      deleteFile: vi.fn().mockResolvedValue(undefined),
      getFileStream: vi.fn(),
    };

    queue = {
      add: vi.fn().mockResolvedValue({ id: 'job-1' }),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        DocumentsService,
        { provide: PrismaService, useValue: prisma },
        { provide: StorageService, useValue: storage },
        { provide: getQueueToken(DOCUMENT_INGESTION_QUEUE), useValue: queue },
      ],
    }).compile();

    service = module.get<DocumentsService>(DocumentsService);
  });

  describe('upload', () => {
    it('tải lên tài liệu PDF thành công và lưu vào Database', async () => {
      const mockFile = {
        originalname: 'ai_overview.pdf',
        mimetype: 'application/pdf',
        size: 5 * 1024 * 1024, // 5MB
        buffer: Buffer.from('fake pdf data'),
      } as Express.Multer.File;

      prisma.document.create.mockResolvedValue({
        ...mockDoc,
        title: 'ai_overview',
        originalName: 'ai_overview.pdf',
        fileType: FileType.PDF,
      });

      const result = await service.upload(mockWorkspaceId, mockUserId, mockFile);

      expect(storage.uploadFile).toHaveBeenCalledOnce();
      expect(prisma.document.create).toHaveBeenCalledOnce();
      expect(result.fileType).toBe(FileType.PDF);
    });

    it('tải lên tài liệu DOCX thành công', async () => {
      const mockFile = {
        originalname: 'report.docx',
        mimetype:
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        size: 2 * 1024 * 1024,
        buffer: Buffer.from('fake docx data'),
      } as Express.Multer.File;

      prisma.document.create.mockResolvedValue({
        ...mockDoc,
        fileType: FileType.DOCX,
      });

      const result = await service.upload(mockWorkspaceId, mockUserId, mockFile);
      expect(result.fileType).toBe(FileType.DOCX);
    });

    it('báo lỗi BadRequestException nếu file vượt quá 25MB', async () => {
      const hugeFile = {
        originalname: 'huge.pdf',
        mimetype: 'application/pdf',
        size: 26 * 1024 * 1024, // 26MB
        buffer: Buffer.from(''),
      } as Express.Multer.File;

      await expect(
        service.upload(mockWorkspaceId, mockUserId, hugeFile),
      ).rejects.toThrow(BadRequestException);
    });

    it('báo lỗi BadRequestException nếu định dạng file không được hỗ trợ', async () => {
      const invalidFile = {
        originalname: 'virus.exe',
        mimetype: 'application/x-msdownload',
        size: 1024,
        buffer: Buffer.from(''),
      } as Express.Multer.File;

      await expect(
        service.upload(mockWorkspaceId, mockUserId, invalidFile),
      ).rejects.toThrow(BadRequestException);
    });
  });

  describe('findAll', () => {
    it('trả về danh sách tài liệu có phân trang và meta', async () => {
      prisma.document.count.mockResolvedValue(1);
      prisma.document.findMany.mockResolvedValue([mockDoc]);

      const result = await service.findAll(mockWorkspaceId, {
        page: 1,
        limit: 10,
      });

      expect(result.data).toHaveLength(1);
      expect(result.meta.total).toBe(1);
      expect(result.meta.page).toBe(1);
    });
  });

  describe('findOne', () => {
    it('trả về tài liệu nếu tồn tại trong Workspace', async () => {
      prisma.document.findFirst.mockResolvedValue(mockDoc);

      const result = await service.findOne(mockWorkspaceId, mockDocumentId);
      expect(result.id).toBe(mockDocumentId);
    });

    it('báo lỗi NotFoundException nếu không tìm thấy', async () => {
      prisma.document.findFirst.mockResolvedValue(null);

      await expect(
        service.findOne(mockWorkspaceId, 'invalid-doc'),
      ).rejects.toThrow(NotFoundException);
    });
  });

  describe('delete', () => {
    it('xóa tài liệu khỏi database và đồng thời xóa file trong Storage', async () => {
      prisma.document.findFirst.mockResolvedValue(mockDoc);
      prisma.document.delete.mockResolvedValue(mockDoc);

      const result = await service.delete(mockWorkspaceId, mockDocumentId);

      expect(result.success).toBe(true);
      expect(prisma.document.delete).toHaveBeenCalledWith({
        where: { id: mockDocumentId },
      });
      expect(storage.deleteFile).toHaveBeenCalledWith(mockDoc.storagePath);
    });
  });
});

