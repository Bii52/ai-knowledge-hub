import { IsOptional, IsString, MaxLength } from 'class-validator';

export class CreateConversationDto {
  @IsString()
  @IsOptional()
  @MaxLength(100, { message: 'Tiêu đề cuộc hội thoại tối đa 100 ký tự' })
  title?: string;
}

