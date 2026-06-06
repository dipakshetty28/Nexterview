import "./globals.css";

import { AuthProvider } from "@/components/auth/auth-provider";

export const metadata = {
  title: "Nexterview | AI-Native Engineering Interviews",
  description: "Evaluate real engineering judgment with realistic, AI-enabled technical interviews.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
