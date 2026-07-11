const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getAuthHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const masterKey = localStorage.getItem("creatorarc_master_key") || "";
  return {
    "X-CreatorArc-Key": masterKey,
  };
}

async function request(path: string, options: RequestInit = {}): Promise<any> {
  const url = `${BASE_URL}${path}`;
  const authHeaders = getAuthHeaders();

  const headers = {
    ...authHeaders,
    ...options.headers,
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = "An error occurred";
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorMessage;
    } catch {
      errorMessage = errorText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export const api = {
  // Authentication check
  async testAuth(password: string): Promise<boolean> {
    const url = `${BASE_URL}/`;
    const response = await fetch(url, {
      headers: { "X-CreatorArc-Key": password },
    });
    return response.status !== 401;
  },

  // Job Status
  async getJobStatus(jobId: string): Promise<any> {
    return request(`/jobs/${jobId}`);
  },

  // Text Suite
  async rewriteText(text: string, tone: string): Promise<any> {
    return request("/text/rewrite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, tone }),
    });
  },

  async generateTwitter(topic: string, context?: string): Promise<any> {
    return request("/text/twitter", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, context }),
    });
  },

  async generateLinkedIn(topic: string, context?: string): Promise<any> {
    return request("/text/linkedin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, context }),
    });
  },

  // YouTube Suite
  async submitYouTubeSummary(videoUrl: string): Promise<any> {
    return request("/youtube/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_url: videoUrl }),
    });
  },

  async submitYouTubeTags(videoUrl: string): Promise<any> {
    return request("/youtube/tags", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_url: videoUrl }),
    });
  },

  async submitYouTubeDescription(videoUrl: string): Promise<any> {
    return request("/youtube/description", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_url: videoUrl }),
    });
  },

  // Media Suite
  async submitMediaUpscale(formData: FormData): Promise<any> {
    return request("/media/upscale", {
      method: "POST",
      body: formData, // FormData contains file or image_url and scale
    });
  },

  async submitMediaBgRemoval(formData: FormData): Promise<any> {
    return request("/media/remove-bg", {
      method: "POST",
      body: formData,
    });
  },

  async submitMediaTranscribe(url: string): Promise<any> {
    return request("/media/transcribe-link", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
  },
};
