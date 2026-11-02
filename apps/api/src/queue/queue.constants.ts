export const DOCUMENT_INGESTION_QUEUE = 'document-ingestion';
export const DOCUMENT_INGESTION_JOB = 'process-document';

export interface DocumentIngestionJobData {
  documentId: string;
  workspaceId: string;
  storagePath: string;
  fileType: string;
}

