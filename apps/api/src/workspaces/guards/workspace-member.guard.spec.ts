import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ExecutionContext, ForbiddenException, NotFoundException } from '@nestjs/common';
import { WorkspaceMemberGuard } from './workspace-member.guard.js';
import { PrismaService } from '../../prisma/prisma.service.js';
import { Role } from '@prisma/client';

describe('WorkspaceMemberGuard', () => {
  let guard: WorkspaceMemberGuard;
  let prisma: {
    workspaceMember: {
      findUnique: ReturnType<typeof vi.fn>;
    };
    workspace: {
      findUnique: ReturnType<typeof vi.fn>;
    };
  };

  const createMockExecutionContext = (request: Record<string, any>): ExecutionContext => ({
    switchToHttp: () => ({
      getRequest: () => request as any,
      getResponse: vi.fn() as any,
      getNext: vi.fn() as any,
    }),
    getClass: vi.fn() as any,
    getHandler: vi.fn() as any,
    getArgs: vi.fn() as any,
    getArgByIndex: vi.fn() as any,
    switchToRpc: vi.fn() as any,
    switchToWs: vi.fn() as any,
    getType: vi.fn() as any,
  });

  beforeEach(() => {
    prisma = {
      workspaceMember: {
        findUnique: vi.fn(),
      },
      workspace: {
        findUnique: vi.fn(),
      },
    };

    guard = new WorkspaceMemberGuard(prisma as unknown as PrismaService);
  });

  it('ném ForbiddenException khi không có user trong request', async () => {
    const context = createMockExecutionContext({});

    await expect(guard.canActivate(context)).rejects.toThrow(
      ForbiddenException,
    );
  });

  it('cho phép truy cập khi không có workspaceId trong params hay body', async () => {
    const context = createMockExecutionContext({
      user: { id: 'user-1' },
      params: {},
    });

    const result = await guard.canActivate(context);
    expect(result).toBe(true);
  });

  it('gán workspaceMember vào request và trả về true khi user là thành viên hợp lệ', async () => {
    const mockMember = {
      id: 'member-1',
      workspaceId: 'ws-1',
      userId: 'user-1',
      role: Role.OWNER,
    };

    prisma.workspaceMember.findUnique.mockResolvedValueOnce(mockMember);

    const request: Record<string, any> = {
      user: { id: 'user-1' },
      params: { workspaceId: 'ws-1' },
    };
    const context = createMockExecutionContext(request);

    const result = await guard.canActivate(context);

    expect(result).toBe(true);
    expect(request.workspaceMember).toEqual(mockMember);
    expect(prisma.workspaceMember.findUnique).toHaveBeenCalledWith({
      where: {
        workspaceId_userId: {
          workspaceId: 'ws-1',
          userId: 'user-1',
        },
      },
    });
  });

  it('ném NotFoundException khi workspace không tồn tại trong DB', async () => {
    prisma.workspaceMember.findUnique.mockResolvedValueOnce(null);
    prisma.workspace.findUnique.mockResolvedValueOnce(null);

    const context = createMockExecutionContext({
      user: { id: 'user-1' },
      params: { workspaceId: 'ws-non-existent' },
    });

    await expect(guard.canActivate(context)).rejects.toThrow(NotFoundException);
  });

  it('ném ForbiddenException khi workspace tồn tại nhưng user không phải thành viên', async () => {
    prisma.workspaceMember.findUnique.mockResolvedValueOnce(null);
    prisma.workspace.findUnique.mockResolvedValueOnce({ id: 'ws-1' });

    const context = createMockExecutionContext({
      user: { id: 'user-intruder' },
      params: { workspaceId: 'ws-1' },
    });

    await expect(guard.canActivate(context)).rejects.toThrow(
      ForbiddenException,
    );
  });
});

