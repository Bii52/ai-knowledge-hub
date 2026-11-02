import { Module, Global } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { ConfigService } from '@nestjs/config';
import {
  DOCUMENT_INGESTION_QUEUE,
} from './queue.constants.js';
import { DocumentIngestionProcessor } from './document-ingestion.processor.js';

@Global()
@Module({
  imports: [
    BullModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (configService: ConfigService) => {
        const host = configService.get<string>('REDIS_HOST') ?? 'localhost';
        const port = Number(configService.get<number>('REDIS_PORT') ?? 6379);
        const password = configService.get<string>('REDIS_PASSWORD') || undefined;

        return {
          connection: {
            host,
            port,
            password,
            maxRetriesPerRequest: null,
            enableReadyCheck: false,
          },
        };
      },
    }),
    BullModule.registerQueue({
      name: DOCUMENT_INGESTION_QUEUE,
    }),
  ],
  providers: [DocumentIngestionProcessor],
  exports: [BullModule],
})
export class QueueModule {}

