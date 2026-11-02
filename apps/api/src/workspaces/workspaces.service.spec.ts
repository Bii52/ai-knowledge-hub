import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Test, TestingModule } from '@nestjs/testing';
import {
  NotFoundException,
  ConflictException,
  ForbiddenException,
} from '@nestjs/common';
import { Role } from '@prisma/client';
import { WorkspacesService } from './workspaces.service.js';
import { PrismaService } from '../prisma/prisma.service.js';

describe('WorkspacesService', () => {
  let service: WorkspacesService;
  let prisma: {
    $transaction: ReturnType<typeof vi.fn>;
    workspace: {
      findUnique: ReturnType<typeof vi.fn>;
      update: ReturnType<typeof vi.fn>;
      delete: ReturnType<typeof vi.fn>;
    };
    workspaceMember: {
      findMany: ReturnType<typeof vi.fn>;
      findUnique: ReturnType<typeof vi.fn>;
      create: ReturnType<typeof vi.fn>;
      update: ReturnType<typeof vi.fn>;
      delete: ReturnType<typeof vi.fn>;
    };
    user: {
      findUnique: ReturnType<typeof vi.fn>;
    };
  };

  const mockUserId = 'user-123';
  const mockWorkspaceId = 'ws-456';
  const mockWorkspace = {
    id: mockWorkspaceId,
    name: 'AI Engineering',
    slug: 'ai-engineering-a1b2',
    description: 'Knowledge Hub for AI',
    ownerId: mockUserId,
    createdAt: new Date(),
    updatedAt: new Date(),
  };

  beforeEach(async () => {
    prisma = {
      $transaction: vi.fn(),
      workspace: {
        findUnique: vi.fn(),
        update: vi.fn(),
        delete: vi.fn(),
      },
      workspaceMember: {
        findMany: vi.fn(),
        findUnique: vi.fn(),
        create: vi.fn(),
        update: vi.fn(),
        delete: vi.fn(),
      },
      user: {
        findUnique: vi.fn(),
      },
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        WorkspacesService,
        { provide: PrismaService, useValue: prisma },
      ],
    }).compile();

    service = module.get<WorkspacesService>(WorkspacesService);
  });

  describe('create', () => {
    it('tạo workspace và gán quyền OWNER cho người tạo trong một transaction', async () => {
      prisma.$transaction.mockImplementation(async (callback) => {
        const tx = {
          workspace: {
            create: vi.fn().mockResolvedValue(mockWorkspace),
          },
          workspaceMember: {
            create: vi.fn().mockResolvedValue({
              id: 'member-1',
              workspaceId: mockWorkspaceId,
              userId: mockUserId,
              role: Role.OWNER,
            }),
          },
        };
        return callback(tx);
      });

      const result = await service.create(mockUserId, {
        name: 'AI Engineering',
        description: 'Knowledge Hub for AI',
      });

      expect(result.id).toBe(mockWorkspaceId);
      expect(result.role).toBe(Role.OWNER);
      expect(prisma.$transaction).toHaveBeenCalledOnce();
    });
  });

  describe('findOne', () => {
    it('trả về chi tiết workspace nếu tồn tại', async () => {
      prisma.workspace.findUnique.mockResolvedValue(mockWorkspace);

      const result = await service.findOne(mockWorkspaceId);
      expect(result.id).toBe(mockWorkspaceId);
      expect(result.name).toBe('AI Engineering');
    });

    it('báo lỗi NotFoundException nếu không tìm thấy workspace', async () => {
      prisma.workspace.findUnique.mockResolvedValue(null);

      await expect(service.findOne('invalid-id')).rejects.toThrow(
        NotFoundException,
      );
    });
  });

  describe('inviteMember', () => {
    it('thêm thành viên mới thành công khi email tồn tại trên hệ thống', async () => {
      prisma.user.findUnique.mockResolvedValue({
        id: 'user-789',
        email: 'collaborator@example.com',
      });
      prisma.workspaceMember.findUnique.mockResolvedValue(null);
      prisma.workspaceMember.create.mockResolvedValue({
        id: 'member-2',
        workspaceId: mockWorkspaceId,
        userId: 'user-789',
        role: Role.MEMBER,
      });

      const result = await service.inviteMember(mockWorkspaceId, {
        email: 'collaborator@example.com',
        role: Role.MEMBER,
      });

      expect(result.role).toBe(Role.MEMBER);
      expect(prisma.workspaceMember.create).toHaveBeenCalledOnce();
    });

    it('báo lỗi ForbiddenException nếu cố gắng mời với vai trò OWNER', async () => {
      await expect(
        service.inviteMember(mockWorkspaceId, {
          email: 'test@example.com',
          role: Role.OWNER,
        }),
      ).rejects.toThrow(ForbiddenException);
    });

    it('báo lỗi NotFoundException nếu email không có tài khoản trên hệ thống', async () => {
      prisma.user.findUnique.mockResolvedValue(null);

      await expect(
        service.inviteMember(mockWorkspaceId, {
          email: 'unknown@example.com',
          role: Role.MEMBER,
        }),
      ).rejects.toThrow(NotFoundException);
    });

    it('báo lỗi ConflictException nếu người dùng đã là thành viên', async () => {
      prisma.user.findUnique.mockResolvedValue({
        id: 'user-789',
        email: 'already@example.com',
      });
      prisma.workspaceMember.findUnique.mockResolvedValue({
        id: 'member-exist',
      });

      await expect(
        service.inviteMember(mockWorkspaceId, {
          email: 'already@example.com',
          role: Role.MEMBER,
        }),
      ).rejects.toThrow(ConflictException);
    });
  });

  describe('updateMemberRole', () => {
    it('thay đổi vai trò của thành viên thành công', async () => {
      prisma.workspaceMember.findUnique.mockResolvedValue({
        id: 'member-2',
        workspaceId: mockWorkspaceId,
        role: Role.MEMBER,
      });
      prisma.workspaceMember.update.mockResolvedValue({
        id: 'member-2',
        role: Role.ADMIN,
      });

      const result = await service.updateMemberRole(mockWorkspaceId, 'member-2', {
        role: Role.ADMIN,
      });

      expect(result.role).toBe(Role.ADMIN);
    });

    it('báo lỗi ForbiddenException nếu cố thay đổi vai trò của OWNER', async () => {
      prisma.workspaceMember.findUnique.mockResolvedValue({
        id: 'member-owner',
        workspaceId: mockWorkspaceId,
        role: Role.OWNER,
      });

      await expect(
        service.updateMemberRole(mockWorkspaceId, 'member-owner', {
          role: Role.ADMIN,
        }),
      ).rejects.toThrow(ForbiddenException);
    });
  });

  describe('removeMember', () => {
    it('xóa thành viên thành công', async () => {
      prisma.workspaceMember.findUnique.mockResolvedValue({
        id: 'member-2',
        workspaceId: mockWorkspaceId,
        role: Role.MEMBER,
      });
      prisma.workspaceMember.delete.mockResolvedValue({});

      const result = await service.removeMember(mockWorkspaceId, 'member-2');
      expect(result.success).toBe(true);
    });

    it('báo lỗi ForbiddenException nếu cố gắng xóa OWNER', async () => {
      prisma.workspaceMember.findUnique.mockResolvedValue({
        id: 'member-owner',
        workspaceId: mockWorkspaceId,
        role: Role.OWNER,
      });

      await expect(
        service.removeMember(mockWorkspaceId, 'member-owner'),
      ).rejects.toThrow(ForbiddenException);
    });
  });
});

