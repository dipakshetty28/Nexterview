export type UserRole = "ADMIN" | "INTERVIEWER" | "CANDIDATE";

export type Organization = {
  id: string;
  name: string;
  slug: string;
};

export type OrganizationMembership = {
  role: UserRole;
  organization: Organization;
};

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  organizations: OrganizationMembership[];
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: User;
};

export type DashboardResponse = {
  user: User;
  organizations: OrganizationMembership[];
};
