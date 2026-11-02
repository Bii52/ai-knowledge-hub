import { IsArray, IsNotEmpty, IsOptional, IsString } from 'class-validator';

export class SendMessageDto {
  @IsString()
  @IsNotEmpty({ message: 'Nội dung câu hỏi không được để trống' })
  content!: string;

  @IsArray({ message: 'Danh sách ID tài liệu phải là một mảng' })
  @IsString({ each: true, message: 'ID tài liệu phải là chuỗi' })
  @IsOptional()
  documentIds?: string[];
}

