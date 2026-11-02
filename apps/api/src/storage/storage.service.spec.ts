import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Test, TestingModule } from '@nestjs/testing';
import { ConfigService } from '@nestjs/config';
import { StorageService } from './storage.service.js';
import { S3Client } from '@aws-sdk/client-s3';
import { Readable } from 'stream';

vi.mock('@aws-sdk/client-s3', () => {
  const S3ClientMock = vi.fn();
  S3ClientMock.prototype.send = vi.fn();

  class MockCommand {
    input: any;
    constructor(input: any) {
      this.input = input;
    }
  }

  return {
    S3Client: S3ClientMock,
    PutObjectCommand: class PutObjectCommand extends MockCommand {},
    DeleteObjectCommand: class DeleteObjectCommand extends MockCommand {},
    GetObjectCommand: class GetObjectCommand extends MockCommand {},
    HeadBucketCommand: class HeadBucketCommand extends MockCommand {},
    CreateBucketCommand: class CreateBucketCommand extends MockCommand {},
  };
});

describe('StorageService', () => {
  let service: StorageService;
  let mockSend: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    mockSend = vi.fn().mockResolvedValue({});
    (S3Client.prototype.send as any) = mockSend;

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        StorageService,
        {
          provide: ConfigService,
          useValue: {
            get: vi.fn().mockImplementation((key: string) => {
              if (key === 'STORAGE_ENDPOINT') return 'localhost';
              if (key === 'STORAGE_PORT') return '9000';
              if (key === 'STORAGE_USE_SSL') return 'false';
              if (key === 'STORAGE_ACCESS_KEY') return 'minioadmin';
              if (key === 'STORAGE_SECRET_KEY') return 'minioadmin';
              if (key === 'STORAGE_BUCKET_NAME') return 'test-bucket';
              return null;
            }),
          },
        },
      ],
    }).compile();

    service = module.get<StorageService>(StorageService);
  });

  describe('uploadFile', () => {
    it('gửi lệnh PutObjectCommand và trả về key lưu trữ', async () => {
      const buffer = Buffer.from('test document content');
      const key = 'workspaces/ws-1/doc-1.pdf';

      const result = await service.uploadFile(key, buffer, 'application/pdf');

      expect(mockSend).toHaveBeenCalledOnce();
      expect(result).toBe(key);
    });
  });

  describe('deleteFile', () => {
    it('gửi lệnh DeleteObjectCommand để xóa file', async () => {
      const key = 'workspaces/ws-1/doc-1.pdf';

      await service.deleteFile(key);

      expect(mockSend).toHaveBeenCalledOnce();
    });
  });

  describe('getFileStream', () => {
    it('gửi lệnh GetObjectCommand và trả về Readable stream', async () => {
      const mockStream = new Readable();
      mockStream._read = () => {};
      mockSend.mockResolvedValueOnce({ Body: mockStream });

      const stream = await service.getFileStream('workspaces/ws-1/doc-1.pdf');

      expect(mockSend).toHaveBeenCalledOnce();
      expect(stream).toBe(mockStream);
    });
  });
});

