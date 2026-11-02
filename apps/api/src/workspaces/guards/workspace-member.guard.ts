import {
  CanActivate,
  ExecutionContext,
  ForbiddenException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { PrismaService } from '../../prisma/prisma.service.js';

@Injectable()
export class WorkspaceMemberGuard implements CanActivate {
  constructor(private readonly prisma: PrismaService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user) {
      throw new ForbiddenException('Yêu cầu xác thực người dùng trước');
    }

    const workspaceId =
      request.params?.workspaceId ?? request.body?.workspaceId;

    if (!workspaceId) {
      return true;
    }

    const member = await this.prisma.workspaceMember.findUnique({
      where: {
        workspaceId_userId: {
          workspaceId,
          userId: user.id,
        },
      },
    });

    if (!member) {
      // Check if workspace even exists to return appropriate error
      const workspaceExists = await this.prisma.workspace.findUnique({
        where: { id: workspaceId },
        select: { id: true },
      });

      if (!workspaceExists) {
        throw new NotFoundException('Workspace không tồn tại');
      }

      throw new ForbiddenException(
        'Bạn không phải là thành viên của Workspace này',
      );
    }

    // Attach verified member info to request context
    request.workspaceMember = member;
    return true;
  }
}

