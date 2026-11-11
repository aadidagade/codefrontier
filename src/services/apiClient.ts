export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
  error?: string;
}

export interface ApiClientConfig {
  baseUrl: string;
  useMock: boolean;
  mockLatencyMs: number;
}

const DEFAULT_CONFIG: ApiClientConfig = {
  baseUrl:
    (import.meta.env.VITE_API_BASE_URL as string) ||
    (import.meta.env.VITE_API_URL as string) ||
    'http://localhost:8000/api/v1',
  useMock: true,
  mockLatencyMs: 300,
};

class ApiClient {
  private config: ApiClientConfig;

  constructor(config: Partial<ApiClientConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  private async simulateLatency(): Promise<void> {
    if (this.config.useMock && this.config.mockLatencyMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, this.config.mockLatencyMs));
    }
  }

  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('kh_auth_token');
    return {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  async executeMock<T>(mockFn: () => T | Promise<T>): Promise<ApiResponse<T>> {
    await this.simulateLatency();
    try {
      const result = await mockFn();
      return {
        data: result,
        status: 200,
        message: 'Success',
      };
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      return {
        data: null as unknown as T,
        status: 400,
        error: errorMsg,
      };
    }
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    if (this.config.useMock) {
      throw new Error(`Real request called while useMock is enabled for ${endpoint}`);
    }

    const url = `${this.config.baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getAuthHeaders(),
        ...options.headers,
      },
    });

    const json = await response.json();
    if (!response.ok) {
      throw new Error(json.message || `Request failed with status ${response.status}`);
    }

    return {
      data: json.data || json,
      status: response.status,
    };
  }
}

export const apiClient = new ApiClient();
