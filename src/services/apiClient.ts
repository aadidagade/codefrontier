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
    '/api/v1',
  useMock: false,
  mockLatencyMs: 0,
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
    const token = localStorage.getItem('kh_auth_token') || localStorage.getItem('token');
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
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    // If endpoint already starts with /api/v1, don't duplicate
    const url = endpoint.startsWith('http')
      ? endpoint
      : endpoint.startsWith('/api/')
      ? endpoint
      : `${this.config.baseUrl}${cleanEndpoint}`;

    const headers = {
      ...this.getAuthHeaders(),
      ...options.headers,
    };

    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers,
      });
    } catch (err: unknown) {
      const netError = err instanceof Error ? err.message : 'Network request failed';
      throw new Error(`Failed to connect to backend service: ${netError}`);
    }

    let json: any = {};
    const text = await response.text();
    if (text) {
      try {
        json = JSON.parse(text);
      } catch {
        json = { message: text };
      }
    }

    if (!response.ok) {
      const errorMsg =
        json.detail ||
        json.message ||
        json.error ||
        `Request failed with status ${response.status}: ${response.statusText}`;
      throw new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
    }

    return {
      data: (json && json.data !== undefined ? json.data : json) as T,
      status: response.status,
      message: json?.message,
    };
  }

  async get<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  async post<T>(endpoint: string, body?: any, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  async patch<T>(endpoint: string, body?: any, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  async put<T>(endpoint: string, body?: any, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
