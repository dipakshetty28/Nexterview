import "./globals.css";

import { AuthProvider } from "@/components/auth/auth-provider";

export const metadata = {
  title: "Nexterview",
  description: "AI-native technical interview platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
