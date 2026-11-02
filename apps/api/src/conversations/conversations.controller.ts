import {
  Controller,
  Get,
  Post,
  Patch,
  Delete,
  Param,
  Body,
  UseGuards,
  HttpCode,
  HttpStatus,
} from '@nestjs/common';
import { ConversationsService } from './conversations.service.js';
import { CreateConversationDto } from './dto/create-conversation.dto.js';
import { SendMessageDto } from './dto/send-message.dto.js';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard.js';
import { WorkspaceMemberGuard } from '../workspaces/guards/workspace-member.guard.js';
import { CurrentUser } from '../auth/decorators/current-user.decorator.js';

@Controller('workspaces/:workspaceId/conversations')
@UseGuards(JwtAuthGuard, WorkspaceMemberGuard)
export class ConversationsController {
  constructor(private readonly conversationsService: ConversationsService) {}

  @Post()
  @HttpCode(HttpStatus.CREATED)
  async create(
    @Param('workspaceId') workspaceId: string,
    @CurrentUser('id') userId: string,
    @Body() dto: CreateConversationDto,
  ) {
    return this.conversationsService.create(workspaceId, userId, dto);
  }

  @Get()
  async findAll(
    @Param('workspaceId') workspaceId: string,
    @CurrentUser('id') userId: string,
  ) {
    return this.conversationsService.findAll(workspaceId, userId);
  }

  @Get(':conversationId')
  async findOne(
    @Param('workspaceId') workspaceId: string,
    @Param('conversationId') conversationId: string,
  ) {
    return this.conversationsService.findOne(workspaceId, conversationId);
  }

  @Patch(':conversationId')
  async updateTitle(
    @Param('workspaceId') workspaceId: string,
    @Param('conversationId') conversationId: string,
    @Body('title') title: string,
  ) {
    return this.conversationsService.updateTitle(
      workspaceId,
      conversationId,
      title,
    );
  }

  @Delete(':conversationId')
  async delete(
    @Param('workspaceId') workspaceId: string,
    @Param('conversationId') conversationId: string,
  ) {
    return this.conversationsService.delete(workspaceId, conversationId);
  }

  @Post(':conversationId/messages')
  @HttpCode(HttpStatus.OK)
  async sendMessage(
    @Param('workspaceId') workspaceId: string,
    @Param('conversationId') conversationId: string,
    @CurrentUser('id') userId: string,
    @Body() dto: SendMessageDto,
  ) {
    return this.conversationsService.sendMessage(
      workspaceId,
      conversationId,
      userId,
      dto,
    );
  }
}

