import { IsEnum, IsNotEmpty } from 'class-validator';
import { Role } from '@prisma/client';

export class UpdateMemberRoleDto {
  @IsEnum(Role, { message: 'Vai trò phải là ADMIN hoặc MEMBER' })
  @IsNotEmpty({ message: 'Vai trò không được để trống' })
  role!: Role;
}

