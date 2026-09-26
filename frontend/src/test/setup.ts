import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Unmount React trees rendered during each test so they don't leak state.
afterEach(() => {
    cleanup();
    window.localStorage.clear();
});
