import { AdminService } from "../types";
import { MockAdminService } from "./mock/mockAdminService";
import { ApiAdminService } from "./api/apiAdminService";

export type AdminDataSource = "mock" | "api";

let mockService: MockAdminService | null = null;
let apiService: ApiAdminService | null = null;

const DEFAULT_SOURCE = (import.meta.env.VITE_ADMIN_DATA_SOURCE ?? "api") as AdminDataSource;

export function getAdminService(source: AdminDataSource = DEFAULT_SOURCE): AdminService {
  // Use API service by default for production (persists to database)
  // Use mock service only when explicitly requested (for development/testing)
  if (source === "api") {
    if (!apiService) {
      apiService = new ApiAdminService();
    }
    return apiService;
  }

  if (source === "mock") {
    if (!mockService) {
      mockService = new MockAdminService();
    }
    return mockService;
  }

  throw new Error(`Unknown admin data source: ${source}`);
}

