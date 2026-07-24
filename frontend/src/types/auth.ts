// Cocok dengan backend/app/schemas/auth.py
export type Role = "admin" | "ppic" | "purchasing" | "viewer";

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  is_verified: boolean;
}

export interface LoginResponseData {
  access_token: string;
  token_type: string;
  user: User;
}
