import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ExecutionContext, ForbiddenException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { RolesGuard } from './roles.guard.js';
import { Role } from '@prisma/client';

describe('RolesGuard', () => {
  let guard: RolesGuard;
  let reflector: {
    getAllAndOverride: ReturnType<typeof vi.fn>;
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
    reflector = {
      getAllAndOverride: vi.fn(),
    };

    guard = new RolesGuard(reflector as unknown as Reflector);
  });

  it('cho phép truy cập khi không có decorator vai trò nào', () => {
    reflector.getAllAndOverride.mockReturnValueOnce(null);

    const context = createMockExecutionContext({});
    const result = guard.canActivate(context);

    expect(result).toBe(true);
  });

  it('cho phép truy cập khi danh sách vai trò yêu cầu là rỗng', () => {
    reflector.getAllAndOverride.mockReturnValueOnce([]);

    const context = createMockExecutionContext({});
    const result = guard.canActivate(context);

    expect(result).toBe(true);
  });

  it('ném ForbiddenException khi không tìm thấy workspaceMember trong request', () => {
    reflector.getAllAndOverride.mockReturnValueOnce([Role.OWNER, Role.ADMIN]);

    const context = createMockExecutionContext({});

    expect(() => guard.canActivate(context)).toThrow(ForbiddenException);
  });

  it('cho phép truy cập khi vai trò của member khớp với vai trò yêu cầu', () => {
    reflector.getAllAndOverride.mockReturnValueOnce([Role.OWNER, Role.ADMIN]);

    const context = createMockExecutionContext({
      workspaceMember: { id: 'm-1', role: Role.ADMIN },
    });

    const result = guard.canActivate(context);
    expect(result).toBe(true);
  });

  it('ném ForbiddenException khi vai trò của member không nằm trong vai trò yêu cầu', () => {
    reflector.getAllAndOverride.mockReturnValueOnce([Role.OWNER, Role.ADMIN]);

    const context = createMockExecutionContext({
      workspaceMember: { id: 'm-2', role: Role.MEMBER },
    });

    expect(() => guard.canActivate(context)).toThrow(ForbiddenException);
  });
});

