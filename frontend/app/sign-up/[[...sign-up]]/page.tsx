import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="flex min-h-full flex-1 items-center justify-center bg-zinc-50 px-4 py-16 dark:bg-black">
      <SignUp forceRedirectUrl="/dashboard" routing="path" path="/sign-up" />
    </div>
  );
}
