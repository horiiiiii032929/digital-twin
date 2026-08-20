import { describe, expect, it } from "vitest"

import { shouldSubmitPromptInput } from "@/lib/prompt-input"

describe("prompt input keyboard behavior", () => {
  it("submits plain Enter but not line breaks or IME composition", () => {
    expect(
      shouldSubmitPromptInput({
        key: "Enter",
        shiftKey: false,
        isComposing: false,
        keyCode: 13,
      }),
    ).toBe(true)
    expect(
      shouldSubmitPromptInput({
        key: "Enter",
        shiftKey: true,
        isComposing: false,
        keyCode: 13,
      }),
    ).toBe(false)
    expect(
      shouldSubmitPromptInput({
        key: "Enter",
        shiftKey: false,
        isComposing: true,
        keyCode: 13,
      }),
    ).toBe(false)
    expect(
      shouldSubmitPromptInput({
        key: "Enter",
        shiftKey: false,
        isComposing: false,
        keyCode: 229,
      }),
    ).toBe(false)
  })
})
