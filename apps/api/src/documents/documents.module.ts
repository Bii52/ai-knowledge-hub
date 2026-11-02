import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { DocumentsService } from './documents.service.js';
import { DocumentsController } from './documents.controller.js';
import { WorkspacesModule } from '../workspaces/workspaces.module.js';
import { DOCUMENT_INGESTION_QUEUE } from '../queue/queue.constants.js';

@Module({
  imports: [
    WorkspacesModule,
    BullModule.registerQueue({
      name: DOCUMENT_INGESTION_QUEUE,
    }),
  ],
  controllers: [DocumentsController],
  providers: [DocumentsService],
  exports: [DocumentsService],
})
export class DocumentsModule {}
