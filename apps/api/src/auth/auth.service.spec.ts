import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Test, TestingModule } from '@nestjs/testing';
import { ConfigService } from '@nestjs/config';
import { JwtService } from '@nestjs/jwt';
import { ConflictException, UnauthorizedException } from '@nestjs/common';
import * as bcrypt from 'bcrypt';
import { AuthService } from './auth.service.js';
import { UsersService } from '../users/users.service.js';
import { PrismaService } from '../prisma/prisma.service.js';

describe('AuthService', () => {
  let authService: AuthService;
  let usersService: { findByEmail: ReturnType<typeof vi.fn>; create: ReturnType<typeof vi.fn>; findById: ReturnType<typeof vi.fn> };
  let prismaService: { refreshToken: { create: ReturnType<typeof vi.fn>; findUnique: ReturnType<typeof vi.fn>; delete: ReturnType<typeof vi.fn>; deleteMany: ReturnType<typeof vi.fn> } };
  let jwtService: { signAsync: ReturnType<typeof vi.fn>; verifyAsync: ReturnType<typeof vi.fn> };

  const mockUser = {
    id: 'user-uuid-1',
    email: 'test@example.com',
    passwordHash: '',
    fullName: 'Test User',
    avatarUrl: null,
    createdAt: new Date(),
    updatedAt: new Date(),
  };

  beforeEach(async () => {
    mockUser.passwordHash = await bcrypt.hash('password123', 10);

    usersService = {
      findByEmail: vi.fn(),
      create: vi.fn(),
      findById: vi.fn(),
    };

    prismaService = {
      refreshToken: {
        create: vi.fn().mockResolvedValue({ id: 'token-uuid', token: 'mock-refresh' }),
        findUnique: vi.fn(),
        delete: vi.fn(),
        deleteMany: vi.fn(),
      },
    };

    jwtService = {
      signAsync: vi.fn().mockImplementation((payload, options) => {
        return Promise.resolve(`jwt-${options.expiresIn}-${payload.email}`);
      }),
      verifyAsync: vi.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        AuthService,
        { provide: UsersService, useValue: usersService },
        { provide: PrismaService, useValue: prismaService },
        { provide: JwtService, useValue: jwtService },
        {
          provide: ConfigService,
          useValue: {
            get: vi.fn().mockImplementation((key: string) => {
              if (key === 'JWT_ACCESS_SECRET') return 'test-access-secret';
              if (key === 'JWT_REFRESH_SECRET') return 'test-refresh-secret';
              if (key === 'JWT_ACCESS_EXPIRES_IN') return '15m';
              if (key === 'JWT_REFRESH_EXPIRES_IN') return '7d';
              return null;
            }),
          },
        },
      ],
    }).compile();

    authService = module.get<AuthService>(AuthService);
  });

  describe('register', () => {
    it('thành công tạo tài khoản mới và trả về tokens', async () => {
      usersService.findByEmail.mockResolvedValue(null);
      usersService.create.mockResolvedValue(mockUser);

      const result = await authService.register({
        email: 'test@example.com',
        password: 'password123',
        fullName: 'Test User',
      });

      expect(result.user.email).toBe('test@example.com');
      expect(result.tokens.accessToken).toBeDefined();
      expect(result.tokens.refreshToken).toBeDefined();
      expect(usersService.create).toHaveBeenCalledOnce();
      expect(prismaService.refreshToken.create).toHaveBeenCalledOnce();
    });

    it('báo lỗi ConflictException nếu email đã tồn tại', async () => {
      usersService.findByEmail.mockResolvedValue(mockUser);

      await expect(
        authService.register({
          email: 'test@example.com',
          password: 'password123',
          fullName: 'Test User',
        }),
      ).rejects.toThrow(ConflictException);
    });
  });

  describe('login', () => {
    it('thành công đăng nhập với đúng email và mật khẩu', async () => {
      usersService.findByEmail.mockResolvedValue(mockUser);

      const result = await authService.login({
        email: 'test@example.com',
        password: 'password123',
      });

      expect(result.user.id).toBe(mockUser.id);
      expect(result.tokens.accessToken).toBeDefined();
      expect(result.tokens.refreshToken).toBeDefined();
    });

    it('báo lỗi UnauthorizedException nếu email không tồn tại', async () => {
      usersService.findByEmail.mockResolvedValue(null);

      await expect(
        authService.login({
          email: 'nonexistent@example.com',
          password: 'password123',
        }),
      ).rejects.toThrow(UnauthorizedException);
    });

    it('báo lỗi UnauthorizedException nếu sai mật khẩu', async () => {
      usersService.findByEmail.mockResolvedValue(mockUser);

      await expect(
        authService.login({
          email: 'test@example.com',
          password: 'wrongpassword',
        }),
      ).rejects.toThrow(UnauthorizedException);
    });
  });

  describe('refresh', () => {
    it('thành công cấp phát token mới với refresh token hợp lệ', async () => {
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 5);

      jwtService.verifyAsync.mockResolvedValue({
        sub: 'user-uuid-1',
        email: 'test@example.com',
      });

      prismaService.refreshToken.findUnique.mockResolvedValue({
        id: 'token-id-1',
        token: 'valid-refresh-token',
        userId: 'user-uuid-1',
        expiresAt: futureDate,
      });

      prismaService.refreshToken.delete.mockResolvedValue({});

      const tokens = await authService.refresh({
        refreshToken: 'valid-refresh-token',
      });

      expect(tokens.accessToken).toBeDefined();
      expect(tokens.refreshToken).toBeDefined();
      expect(prismaService.refreshToken.delete).toHaveBeenCalledWith({
        where: { id: 'token-id-1' },
      });
    });

    it('báo lỗi UnauthorizedException nếu token đã hết hạn', async () => {
      const pastDate = new Date();
      pastDate.setDate(pastDate.getDate() - 1);

      jwtService.verifyAsync.mockResolvedValue({
        sub: 'user-uuid-1',
        email: 'test@example.com',
      });

      prismaService.refreshToken.findUnique.mockResolvedValue({
        id: 'token-id-1',
        token: 'expired-refresh-token',
        userId: 'user-uuid-1',
        expiresAt: pastDate,
      });

      await expect(
        authService.refresh({ refreshToken: 'expired-refresh-token' }),
      ).rejects.toThrow(UnauthorizedException);
    });
  });
});

