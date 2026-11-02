import { createParamDecorator, ExecutionContext } from '@nestjs/common';
import type { UserWithoutPassword } from '../../users/users.service.js';

export const CurrentUser = createParamDecorator(
  (
    data: keyof UserWithoutPassword | undefined,
    ctx: ExecutionContext,
  ): UserWithoutPassword | unknown => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user as UserWithoutPassword;

    if (!user) {
      return null;
    }

    return data ? user[data] : user;
  },
);

