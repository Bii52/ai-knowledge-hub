import { createParamDecorator, ExecutionContext } from '@nestjs/common';
import type { WorkspaceMember } from '@prisma/client';

export const CurrentWorkspaceMember = createParamDecorator(
  (
    data: keyof WorkspaceMember | undefined,
    ctx: ExecutionContext,
  ): WorkspaceMember | unknown => {
    const request = ctx.switchToHttp().getRequest();
    const member = request.workspaceMember as WorkspaceMember;

    if (!member) {
      return null;
    }

    return data ? member[data] : member;
  },
);

