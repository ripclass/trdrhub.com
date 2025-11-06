import { AdminService } from "../types";
import { MockAdminService } from "./mock/mockAdminService";

export type AdminDataSource = "mock" | "api";

let mockService: MockAdminService | null = null;

export function getAdminService(source: AdminDataSource = "mock"): AdminService {
  if (source === "mock") {
    if (!mockService) {
      mockService = new MockAdminService();
    }
    return mockService;
  }

  throw new Error("API data source not implemented yet");
}

