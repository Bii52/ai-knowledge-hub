import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { DocumentIngestionProcessor } from './document-ingestion.processor.js';
import { PrismaService } from '../prisma/prisma.service.js';
import { ConfigService } from '@nestjs/config';
import { DocumentStatus } from '@prisma/client';
import type { Job } from 'bullmq';
import type { DocumentIngestionJobData } from './queue.constants.js';

describe('DocumentIngestionProcessor', () => {
  let processor: DocumentIngestionProcessor;
  let prisma: {
    document: {
      update: ReturnType<typeof vi.fn>;
    };
  };
  let configService: {
    get: ReturnType<typeof vi.fn>;
  };

  const mockJob: Partial<Job<DocumentIngestionJobData>> = {
    id: 'job-123',
    data: {
      documentId: 'doc-1',
      workspaceId: 'ws-1',
      storagePath: 'workspaces/ws-1/doc-1.pdf',
      fileType: 'pdf',
    },
  };

  beforeEach(() => {
    prisma = {
      document: {
        update: vi.fn().mockResolvedValue({}),
      },
    };

    configService = {
      get: vi.fn().mockReturnValue('http://localhost:8000'),
    };

    processor = new DocumentIngestionProcessor(
      prisma as unknown as PrismaService,
      configService as unknown as ConfigService,
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('cập nhật PROCESSING, gọi AI Service và hoàn tất sang COMPLETED khi thành công', async () => {
    const mockFetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
    });
    vi.stubGlobal('fetch', mockFetch);

    await processor.process(mockJob as Job<DocumentIngestionJobData>);

    // 1. Phải cập nhật sang PROCESSING
    expect(prisma.document.update).toHaveBeenNthCalledWith(1, {
      where: { id: 'doc-1' },
      data: {
        status: DocumentStatus.PROCESSING,
        errorMessage: null,
      },
    });

    // 2. Phải gọi AI Service đúng endpoint và body
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/ingest',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: 'doc-1',
          workspace_id: 'ws-1',
          storage_path: 'workspaces/ws-1/doc-1.pdf',
          file_type: 'pdf',
        }),
      }),
    );

    // 3. Phải cập nhật sang COMPLETED
    expect(prisma.document.update).toHaveBeenNthCalledWith(2, {
      where: { id: 'doc-1' },
      data: {
        status: DocumentStatus.COMPLETED,
      },
    });
  });

  it('xử lý an toàn khi AI Service phản hồi lỗi mạng hoặc offline', async () => {
    const mockFetch = vi.fn().mockRejectedValueOnce(new Error('Connection refused'));
    vi.stubGlobal('fetch', mockFetch);

    await processor.process(mockJob as Job<DocumentIngestionJobData>);

    // Vẫn hoàn tất sang COMPLETED và ghi log fallback
    expect(prisma.document.update).toHaveBeenLastCalledWith({
      where: { id: 'doc-1' },
      data: {
        status: DocumentStatus.COMPLETED,
      },
    });
  });

  it('chuyển trạng thái sang FAILED và ném lại lỗi khi xảy ra sự cố ngoại lệ', async () => {
    prisma.document.update.mockRejectedValueOnce(new Error('Database error'));

    await expect(
      processor.process(mockJob as Job<DocumentIngestionJobData>),
    ).rejects.toThrow('Database error');

    // Lần gọi thứ hai trong catch block để đánh dấu FAILED
    expect(prisma.document.update).toHaveBeenLastCalledWith({
      where: { id: 'doc-1' },
      data: {
        status: DocumentStatus.FAILED,
        errorMessage: 'Database error',
      },
    });
  });
});

