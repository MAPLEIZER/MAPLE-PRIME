import { describe, expect, it } from "vitest";
import { prepareContribution } from "./contribution";

describe("mobile contribution privacy boundary", () => {
  it("drops message content and call duration before upload", () => {
    const output = prepareContribution({kind: "sms_sender", institutionHint: "Example Credit", senderIdentifier: "EXAMPLE", appPackage: "com.example.credit", rawMessageBody: "private message body", callDurationSeconds: 47, shareConsent: true});
    expect(output).not.toHaveProperty("rawMessageBody");
    expect(output).not.toHaveProperty("callDurationSeconds");
    expect(output.senderIdentifier).toBe("EXAMPLE");
  });
  it("refuses non-consensual sharing", () => {
    expect(() => prepareContribution({ kind: "app_package", shareConsent: false })).toThrow();
  });
});
