"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RandomFusionPage() {
  const router = useRouter();

  useEffect(() => {
    fetch(`/api/fusion/random?_=${Date.now()}`)
      .then((r) => r.json())
      .then((data) => {
        if (data?.head_id && data?.body_id) {
          router.replace(`/fusion/${data.head_id}/${data.body_id}`);
        } else {
          router.replace("/fusion");
        }
      })
      .catch(() => router.replace("/fusion"));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center space-y-3">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-sm text-if-text-xs">Fusion aléatoire en cours…</p>
      </div>
    </div>
  );
}
