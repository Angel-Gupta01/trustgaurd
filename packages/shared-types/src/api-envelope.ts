// packages/shared-types/src/api-envelope.ts

export interface ApiError {
  code: string;
  message: string;
  field?: string;
}
 
export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
  requestId: string;
}
