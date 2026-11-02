import {
  Controller,
  Get,
  Post,
  Delete,
  Param,
  Query,
  UseGuards,
  UseInterceptors,
  UploadedFile,
  HttpCode,
  HttpStatus,
  StreamableFile,
  Res,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { DocumentsService } from './documents.service.js';
import { QueryDocumentsDto } from './dto/query-documents.dto.js';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard.js';
import { WorkspaceMemberGuard } from '../workspaces/guards/workspace-member.guard.js';
import { RolesGuard } from '../workspaces/guards/roles.guard.js';
import { Roles } from '../workspaces/decorators/roles.decorator.js';
import { CurrentUser } from '../auth/decorators/current-user.decorator.js';
import { Role } from '@prisma/client';
import type { Response } from 'express';

@Controller('workspaces/:workspaceId/documents')
@UseGuards(JwtAuthGuard, WorkspaceMemberGuard)
export class DocumentsController {
  constructor(private readonly documentsService: DocumentsService) {}

  @Post('upload')
  @UseGuards(RolesGuard)
  @Roles(Role.OWNER, Role.ADMIN)
  @UseInterceptors(FileInterceptor('file'))
  @HttpCode(HttpStatus.CREATED)
  async upload(
    @Param('workspaceId') workspaceId: string,
    @CurrentUser('id') userId: string,
    @UploadedFile() file: Express.Multer.File,
  ) {
    return this.documentsService.upload(workspaceId, userId, file);
  }

  @Get()
  async findAll(
    @Param('workspaceId') workspaceId: string,
    @Query() query: QueryDocumentsDto,
  ) {
    return this.documentsService.findAll(workspaceId, query);
  }

  @Get(':documentId')
  async findOne(
    @Param('workspaceId') workspaceId: string,
    @Param('documentId') documentId: string,
  ) {
    return this.documentsService.findOne(workspaceId, documentId);
  }

  @Delete(':documentId')
  @UseGuards(RolesGuard)
  @Roles(Role.OWNER, Role.ADMIN)
  async delete(
    @Param('workspaceId') workspaceId: string,
    @Param('documentId') documentId: string,
  ) {
    return this.documentsService.delete(workspaceId, documentId);
  }

  @Get(':documentId/download')
  async download(
    @Param('workspaceId') workspaceId: string,
    @Param('documentId') documentId: string,
    @Res({ passthrough: true }) res: Response,
  ): Promise<StreamableFile> {
    const { stream, document } = await this.documentsService.getFileStream(
      workspaceId,
      documentId,
    );

    res.set({
      'Content-Type': document.mimeType,
      'Content-Disposition': `attachment; filename="${encodeURIComponent(document.originalName)}"`,
    });

    return new StreamableFile(stream);
  }
}

