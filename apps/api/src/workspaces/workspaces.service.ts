import {
  Injectable,
  NotFoundException,
  ConflictException,
  ForbiddenException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import { CreateWorkspaceDto } from './dto/create-workspace.dto.js';
import { UpdateWorkspaceDto } from './dto/update-workspace.dto.js';
import { InviteMemberDto } from './dto/invite-member.dto.js';
import { UpdateMemberRoleDto } from './dto/update-member-role.dto.js';
import { Role } from '@prisma/client';
import * as crypto from 'crypto';

@Injectable()
export class WorkspacesService {
  constructor(private readonly prisma: PrismaService) {}

  /**
   * Tạo Workspace mới và tự động gán Creator làm OWNER trong một Transaction
   */
  async create(userId: string, dto: CreateWorkspaceDto) {
    const slug = this.generateSlug(dto.name);

    return this.prisma.$transaction(async (tx) => {
      const workspace = await tx.workspace.create({
        data: {
          name: dto.name.trim(),
          slug,
          description: dto.description?.trim(),
          ownerId: userId,
        },
      });

      const member = await tx.workspaceMember.create({
        data: {
          workspaceId: workspace.id,
          userId,
          role: Role.OWNER,
        },
      });

      return {
        ...workspace,
        role: member.role,
      };
    });
  }

  /**
   * Lấy tất cả Workspace mà người dùng đang tham gia
   */
  async findAllForUser(userId: string) {
    const memberships = await this.prisma.workspaceMember.findMany({
      where: { userId },
      include: {
        workspace: {
          include: {
            _count: {
              select: {
                documents: true,
                members: true,
              },
            },
          },
        },
      },
      orderBy: {
        joinedAt: 'desc',
      },
    });

    return memberships.map((m) => ({
      id: m.workspace.id,
      name: m.workspace.name,
      slug: m.workspace.slug,
      description: m.workspace.description,
      ownerId: m.workspace.ownerId,
      role: m.role,
      joinedAt: m.joinedAt,
      createdAt: m.workspace.createdAt,
      updatedAt: m.workspace.updatedAt,
      _count: m.workspace._count,
    }));
  }

  /**
   * Xem thông tin chi tiết một Workspace
   */
  async findOne(workspaceId: string) {
    const workspace = await this.prisma.workspace.findUnique({
      where: { id: workspaceId },
      include: {
        owner: {
          select: {
            id: true,
            email: true,
            fullName: true,
            avatarUrl: true,
          },
        },
        _count: {
          select: {
            documents: true,
            members: true,
            conversations: true,
          },
        },
      },
    });

    if (!workspace) {
      throw new NotFoundException('Workspace không tồn tại');
    }

    return workspace;
  }

  /**
   * Cập nhật thông tin Workspace
   */
  async update(workspaceId: string, dto: UpdateWorkspaceDto) {
    return this.prisma.workspace.update({
      where: { id: workspaceId },
      data: {
        ...(dto.name ? { name: dto.name.trim() } : {}),
        ...(dto.description !== undefined
          ? { description: dto.description?.trim() }
          : {}),
      },
    });
  }

  /**
   * Xóa Workspace (Chỉ OWNER được phép)
   */
  async delete(workspaceId: string) {
    return this.prisma.workspace.delete({
      where: { id: workspaceId },
    });
  }

  /**
   * Danh sách thành viên trong Workspace
   */
  async getMembers(workspaceId: string) {
    return this.prisma.workspaceMember.findMany({
      where: { workspaceId },
      include: {
        user: {
          select: {
            id: true,
            email: true,
            fullName: true,
            avatarUrl: true,
          },
        },
      },
      orderBy: {
        joinedAt: 'asc',
      },
    });
  }

  /**
   * Mời thành viên mới vào Workspace
   */
  async inviteMember(workspaceId: string, dto: InviteMemberDto) {
    if (dto.role === Role.OWNER) {
      throw new ForbiddenException(
        'Không thể thêm thành viên mới với vai trò OWNER',
      );
    }

    const targetUser = await this.prisma.user.findUnique({
      where: { email: dto.email.toLowerCase().trim() },
    });

    if (!targetUser) {
      throw new NotFoundException(
        'Không tìm thấy người dùng với email này trên hệ thống',
      );
    }

    const existingMember = await this.prisma.workspaceMember.findUnique({
      where: {
        workspaceId_userId: {
          workspaceId,
          userId: targetUser.id,
        },
      },
    });

    if (existingMember) {
      throw new ConflictException(
        'Người dùng này đã là thành viên của Workspace',
      );
    }

    return this.prisma.workspaceMember.create({
      data: {
        workspaceId,
        userId: targetUser.id,
        role: dto.role ?? Role.MEMBER,
      },
      include: {
        user: {
          select: {
            id: true,
            email: true,
            fullName: true,
            avatarUrl: true,
          },
        },
      },
    });
  }

  /**
   * Cập nhật vai trò thành viên
   */
  async updateMemberRole(
    workspaceId: string,
    memberId: string,
    dto: UpdateMemberRoleDto,
  ) {
    if (dto.role === Role.OWNER) {
      throw new ForbiddenException(
        'Không thể chuyển vai trò thành viên thành OWNER qua chức năng này',
      );
    }

    const targetMember = await this.prisma.workspaceMember.findUnique({
      where: { id: memberId },
    });

    if (!targetMember || targetMember.workspaceId !== workspaceId) {
      throw new NotFoundException('Không tìm thấy thành viên trong Workspace');
    }

    if (targetMember.role === Role.OWNER) {
      throw new ForbiddenException(
        'Không thể thay đổi vai trò của Chủ sở hữu (OWNER)',
      );
    }

    return this.prisma.workspaceMember.update({
      where: { id: memberId },
      data: { role: dto.role },
      include: {
        user: {
          select: {
            id: true,
            email: true,
            fullName: true,
            avatarUrl: true,
          },
        },
      },
    });
  }

  /**
   * Xóa thành viên khỏi Workspace
   */
  async removeMember(workspaceId: string, memberId: string) {
    const targetMember = await this.prisma.workspaceMember.findUnique({
      where: { id: memberId },
    });

    if (!targetMember || targetMember.workspaceId !== workspaceId) {
      throw new NotFoundException('Không tìm thấy thành viên trong Workspace');
    }

    if (targetMember.role === Role.OWNER) {
      throw new ForbiddenException(
        'Không thể xóa Chủ sở hữu (OWNER) khỏi Workspace',
      );
    }

    await this.prisma.workspaceMember.delete({
      where: { id: memberId },
    });

    return { success: true };
  }

  /**
   * Hàm tiện ích tạo slug URL-friendly duy nhất từ tên workspace
   */
  private generateSlug(name: string): string {
    const baseSlug = name
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[đĐ]/g, 'd')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 40);

    const randomSuffix = crypto.randomBytes(3).toString('hex');
    return `${baseSlug || 'workspace'}-${randomSuffix}`;
  }
}

