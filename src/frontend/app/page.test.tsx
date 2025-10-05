import React from "react";
import { render, screen } from "@testing-library/react";
import HomePage from "./page";

describe("HomePage", () => {
  beforeEach(() => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ items: [], count: 0 }),
    } as unknown as Response);

    class ResizeObserverMock {
      observe() {
        return undefined;
      }
      unobserve() {
        return undefined;
      }
      disconnect() {
        return undefined;
      }
    }

    // @ts-expect-error jsdom lacks ResizeObserver
    global.ResizeObserver = ResizeObserverMock;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the heading", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: /open data insight platform/i })).toBeInTheDocument();
  });
});
