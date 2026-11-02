import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Test, TestingModule } from '@nestjs/testing';
import { UsersService } from './users.service.js';
import { PrismaService } from '../prisma/prisma.service.js';

describe('UsersService', () => {
  let service: UsersService;
  let prisma: {
    user: {
      create: ReturnType<typeof vi.fn>;
      findUnique: ReturnType<typeof vi.fn>;
    };
  };

  const mockUser = {
    id: 'user-uuid-1',
    email: 'test@example.com',
    passwordHash: 'hashedpassword',
    fullName: 'Test User',
    avatarUrl: null,
    createdAt: new Date(),
    updatedAt: new Date(),
  };

  beforeEach(async () => {
    prisma = {
      user: {
        create: vi.fn(),
        findUnique: vi.fn(),
      },
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        UsersService,
        { provide: PrismaService, useValue: prisma },
      ],
    }).compile();

    service = module.get<UsersService>(UsersService);
  });

  describe('create', () => {
    it('tạo người dùng mới với email chuẩn hóa chữ thường', async () => {
      prisma.user.create.mockResolvedValue(mockUser);

      const result = await service.create({
        email: '  TEST@Example.com ',
        passwordHash: 'hashedpassword',
        fullName: ' Test User ',
      });

      expect(prisma.user.create).toHaveBeenCalledWith({
        data: {
          email: 'test@example.com',
          passwordHash: 'hashedpassword',
          fullName: 'Test User',
        },
      });
      expect(result.id).toBe(mockUser.id);
    });
  });

  describe('findByEmail', () => {
    it('tìm người dùng theo email', async () => {
      prisma.user.findUnique.mockResolvedValue(mockUser);

      const result = await service.findByEmail('test@example.com');
      expect(result?.id).toBe(mockUser.id);
      expect(prisma.user.findUnique).toHaveBeenCalledWith({
        where: { email: 'test@example.com' },
      });
    });
  });

  describe('findById', () => {
    it('tìm người dùng theo ID và không trả về passwordHash', async () => {
      const safeUser = {
        id: mockUser.id,
        email: mockUser.email,
        fullName: mockUser.fullName,
        avatarUrl: null,
        createdAt: mockUser.createdAt,
        updatedAt: mockUser.updatedAt,
      };

      prisma.user.findUnique.mockResolvedValue(safeUser);

      const result = await service.findById(mockUser.id);
      expect(result?.id).toBe(mockUser.id);
      expect(result).not.toHaveProperty('passwordHash');
    });
  });
});

