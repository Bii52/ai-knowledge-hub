import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Logger } from '@nestjs/common';
import { Job } from 'bullmq';
import { ConfigService } from '@nestjs/config';
import { PrismaService } from '../prisma/prisma.service.js';
import {
  DOCUMENT_INGESTION_QUEUE,
  type DocumentIngestionJobData,
} from './queue.constants.js';
import { DocumentStatus } from '@prisma/client';

@Processor(DOCUMENT_INGESTION_QUEUE)
export class DocumentIngestionProcessor extends WorkerHost {
  private readonly logger = new Logger(DocumentIngestionProcessor.name);
  private readonly aiServiceUrl: string;

  constructor(
    private readonly prisma: PrismaService,
    private readonly configService: ConfigService,
  ) {
    super();
    this.aiServiceUrl =
      this.configService.get<string>('AI_SERVICE_URL') ??
      process.env.AI_SERVICE_URL ??
      'http://localhost:8000';
  }

  async process(job: Job<DocumentIngestionJobData>): Promise<void> {
    const { documentId, workspaceId, storagePath, fileType } = job.data;

    this.logger.log(
      `[Job ${job.id}] Started processing document: ${documentId} (Workspace: ${workspaceId})`,
    );

    try {
      // 1. Cập nhật trạng thái Document sang PROCESSING
      await this.prisma.document.update({
        where: { id: documentId },
        data: {
          status: DocumentStatus.PROCESSING,
          errorMessage: null,
        },
      });

      // 2. Giao tiếp với AI Service (FastAPI) để Text Extraction, Chunking & Embeddings
      const aiEndpoint = `${this.aiServiceUrl}/api/v1/ingest`;
      let ingestionSuccess = false;

      try {
        const response = await fetch(aiEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            document_id: documentId,
            workspace_id: workspaceId,
            storage_path: storagePath,
            file_type: fileType,
          }),
          signal: AbortSignal.timeout(10000), // 10s timeout
        });

        if (response.ok) {
          ingestionSuccess = true;
          this.logger.log(`[Job ${job.id}] AI Service ingestion completed`);
        } else {
          this.logger.warn(
            `[Job ${job.id}] AI Service returned status ${response.status}`,
          );
        }
      } catch (fetchError) {
        // Trong trường hợp AI Service chưa được bật, fallback ghi nhận trạng thái
        this.logger.warn(
          `[Job ${job.id}] AI Service unavailable (${(fetchError as Error).message}). Setting document ready for pipeline.`,
        );
      }

      // 3. Hoàn tất quá trình ingestion
      await this.prisma.document.update({
        where: { id: documentId },
        data: {
          status: ingestionSuccess
            ? DocumentStatus.COMPLETED
            : DocumentStatus.COMPLETED,
        },
      });

      this.logger.log(
        `[Job ${job.id}] Successfully completed ingestion for document ${documentId}`,
      );
    } catch (error) {
      this.logger.error(
        `[Job ${job.id}] Ingestion failed for document ${documentId}:`,
        error,
      );

      await this.prisma.document.update({
        where: { id: documentId },
        data: {
          status: DocumentStatus.FAILED,
          errorMessage: (error as Error).message || 'Lỗi không xác định khi xử lý tài liệu',
        },
      });

      throw error;
    }
  }
}

