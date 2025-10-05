import React from "react";
import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";

import { ConnectionWizard } from "./connection-wizard";

describe("ConnectionWizard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("submits the form and renders the preview when the API returns success", async () => {
    const spy = vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        status_code: 200,
        reason: "OK",
        content_type: "application/json",
        detected_format: "json" as const,
        record_count: 1,
        schema_fields: ["id"],
        preview: "[{\"id\":1}]",
        preview_truncated: false,
        elapsed_ms: 123,
        request_url: "https://data.example.com/users",
        error: null,
      }),
    } as unknown as Response);

    render(<ConnectionWizard />);

    await userEvent.type(screen.getByLabelText("Open Data Portal"), "data.go.kr");
    await userEvent.type(screen.getByLabelText("Dataset ID"), "users");
    await userEvent.type(screen.getByLabelText("API Base URL"), "https://data.example.com");
    await userEvent.type(screen.getByLabelText("Endpoint Path"), "/datasets/users");
    const submit = screen.getByRole("button", { name: "Test Connection" });
    await userEvent.click(submit);

    await waitFor(() => {
      expect(spy).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId("data-preview")).toBeInTheDocument();
    });

    const [url, options] = spy.mock.calls[0];
    expect(url).toContain("/connections/test");
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.portal_name).toBe("data.go.kr");
    expect(body.dataset_id).toBe("users");
  });
});
