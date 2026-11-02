import { IsEmail, IsEnum, IsNotEmpty, IsOptional } from 'class-validator';
import { Role } from '@prisma/client';

export class InviteMemberDto {
  @IsEmail({}, { message: 'Email không đúng định dạng' })
  @IsNotEmpty({ message: 'Email không được để trống' })
  email!: string;

  @IsEnum(Role, { message: 'Vai trò phải là ADMIN hoặc MEMBER' })
  @IsOptional()
  role?: Role = Role.MEMBER;
}

