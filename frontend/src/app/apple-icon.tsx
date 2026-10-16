import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0f172a",
        }}
      >
        <svg width="132" height="132" viewBox="0 0 64 64">
          <path d="M32 12 52 22 32 32 12 22Z" fill="#2dd4bf" />
          <path d="M15.5 30.2 32 38.4l16.5-8.2L52 32 32 42 12 32Z" fill="#5eead4" />
          <path d="M15.5 40.2 32 48.4l16.5-8.2L52 42 32 52 12 42Z" fill="#99f6e4" />
        </svg>
      </div>
    ),
    size,
  );
}
