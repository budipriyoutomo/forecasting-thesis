// User Management (CR v3.7) — cocok dengan backend/app/schemas/user.py.
import type { Role } from "@/types/auth";

export interface ManagedUser {
  id: string;
  email: string;
  name: string;
  role: Role;
  is_verified: boolean;
  is_active: boolean;
  created_at: string | null;
}

export interface UserCreateInput {
  email: string;
  name: string;
  role: Role;
}

export interface UserUpdateInput {
  name?: string;
  role?: Role;
  is_active?: boolean;
}
