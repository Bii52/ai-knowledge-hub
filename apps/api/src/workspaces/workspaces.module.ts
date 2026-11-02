import { Module } from '@nestjs/common';
import { WorkspacesService } from './workspaces.service.js';
import { WorkspacesController } from './workspaces.controller.js';
import { WorkspaceMemberGuard } from './guards/workspace-member.guard.js';
import { RolesGuard } from './guards/roles.guard.js';

@Module({
  controllers: [WorkspacesController],
  providers: [WorkspacesService, WorkspaceMemberGuard, RolesGuard],
  exports: [WorkspacesService, WorkspaceMemberGuard, RolesGuard],
})
export class WorkspacesModule {}

