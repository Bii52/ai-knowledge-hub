import {
  Injectable,
  Logger,
  OnModuleInit,
  InternalServerErrorException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import {
  S3Client,
  PutObjectCommand,
  DeleteObjectCommand,
  GetObjectCommand,
  HeadBucketCommand,
  CreateBucketCommand,
} from '@aws-sdk/client-s3';
import { Readable } from 'stream';

@Injectable()
export class StorageService implements OnModuleInit {
  private readonly logger = new Logger(StorageService.name);
  private readonly s3Client: S3Client;
  private readonly bucketName: string;

  constructor(private readonly configService: ConfigService) {
    const endpointHost =
      this.configService.get<string>('STORAGE_ENDPOINT') ?? 'localhost';
    const endpointPort = this.configService.get<string>('STORAGE_PORT') ?? '9000';
    const useSsl =
      this.configService.get<string>('STORAGE_USE_SSL') === 'true';

    const protocol = useSsl ? 'https' : 'http';
    const endpoint = `${protocol}://${endpointHost}:${endpointPort}`;

    const accessKeyId =
      this.configService.get<string>('STORAGE_ACCESS_KEY') ?? 'minioadmin';
    const secretAccessKey =
      this.configService.get<string>('STORAGE_SECRET_KEY') ?? 'minioadmin';

    this.bucketName =
      this.configService.get<string>('STORAGE_BUCKET_NAME') ??
      'ai-knowledge-hub';

    this.s3Client = new S3Client({
      endpoint,
      region: 'us-east-1',
      credentials: {
        accessKeyId,
        secretAccessKey,
      },
      forcePathStyle: true, // Required for MinIO
    });
  }

  async onModuleInit(): Promise<void> {
    try {
      await this.ensureBucketExists();
      this.logger.log(`Storage ready with bucket: "${this.bucketName}"`);
    } catch (error) {
      this.logger.warn(
        `Storage connection deferred (MinIO/S3 might not be running yet): ${(error as Error).message}`,
      );
    }
  }

  /**
   * Tải file lên Object Storage
   */
  async uploadFile(
    key: string,
    buffer: Buffer,
    mimeType: string,
  ): Promise<string> {
    try {
      const command = new PutObjectCommand({
        Bucket: this.bucketName,
        Key: key,
        Body: buffer,
        ContentType: mimeType,
      });

      await this.s3Client.send(command);
      this.logger.log(`File uploaded successfully to storage: ${key}`);
      return key;
    } catch (error) {
      this.logger.error(`Storage upload failed for ${key}:`, error);
      throw new InternalServerErrorException(
        'Không thể lưu trữ tệp vào hệ thống Object Storage',
      );
    }
  }

  /**
   * Xóa file khỏi Object Storage
   */
  async deleteFile(key: string): Promise<void> {
    try {
      const command = new DeleteObjectCommand({
        Bucket: this.bucketName,
        Key: key,
      });

      await this.s3Client.send(command);
      this.logger.log(`File deleted successfully from storage: ${key}`);
    } catch (error) {
      this.logger.error(`Storage delete failed for ${key}:`, error);
    }
  }

  /**
   * Lấy luồng dữ liệu file (Stream) để phục vụ tải về
   */
  async getFileStream(key: string): Promise<Readable> {
    try {
      const command = new GetObjectCommand({
        Bucket: this.bucketName,
        Key: key,
      });

      const response = await this.s3Client.send(command);
      return response.Body as Readable;
    } catch (error) {
      this.logger.error(`Storage get stream failed for ${key}:`, error);
      throw new InternalServerErrorException(
        'Không thể đọc tệp từ hệ thống lưu trữ',
      );
    }
  }

  /**
   * Tự động khởi tạo Bucket nếu chưa tồn tại
   */
  private async ensureBucketExists(): Promise<void> {
    try {
      await this.s3Client.send(
        new HeadBucketCommand({ Bucket: this.bucketName }),
      );
    } catch (error: unknown) {
      const statusCode = (error as { $metadata?: { httpStatusCode?: number } })
        ?.$metadata?.httpStatusCode;

      if (statusCode === 404 || (error as { name?: string }).name === 'NotFound') {
        this.logger.log(`Bucket "${this.bucketName}" not found. Creating...`);
        await this.s3Client.send(
          new CreateBucketCommand({ Bucket: this.bucketName }),
        );
        this.logger.log(`Bucket "${this.bucketName}" created successfully.`);
      } else {
        throw error;
      }
    }
  }
}

