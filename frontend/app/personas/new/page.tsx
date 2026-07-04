"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { CalendarDays, FileText, ImageIcon, Mic, Sparkles, Video } from "lucide-react";
import {
  PageTitle,
  StarButton,
  StarInput,
  StarNav,
  StarPanel,
  StarShell,
  TwinkleLabel
} from "@/src/components/StarSite";
import { ensureDemoSession } from "@/src/lib/auth";
import { createPersona, PersonaDraft } from "@/src/lib/persona";
import { ROUTES } from "@/src/lib/routes";

type UploadKind = "照片" | "视频" | "声音" | "文字";

export default function NewPersonaPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [relationship, setRelationship] = useState("");
  const [nickname, setNickname] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [gender, setGender] = useState<"male" | "female" | "unknown">("male");
  const [status, setStatus] = useState<"deceased" | "living" | "other">("deceased");
  const [message, setMessage] = useState("");
  const [uploads, setUploads] = useState<Record<UploadKind, number>>({
    照片: 0,
    视频: 0,
    声音: 0,
    文字: 0
  });
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!name.trim() || !relationship.trim() || !nickname.trim()) {
      setError("请至少填写姓名、与我的关系和 TA 对你的称谓。");
      return;
    }

    const draft: PersonaDraft = {
      name,
      persona_type: status === "living" ? "living_relative" : "deceased_relative",
      status: status === "living" ? "living" : "deceased",
      relationship_to_user: relationship,
      user_nickname_by_persona: nickname,
      gender,
      language: "zh-CN",
      short_bio: [
        birthDate ? `${birthDate} 出生` : "",
        message ? `想对TA说：${message}` : "",
        "由星记创建的专属星星。"
      ]
        .filter(Boolean)
        .join("\n"),
      speaking_style: "温柔、耐心、像夜空里的星光一样陪伴用户。",
      emotional_style: "安静倾听，给予鼓励，不制造虚假的现实承诺。",
      forbidden_expressions: "不要声称自己是真人复活，不要替用户做重大决定。"
    };

    setIsSubmitting(true);
    try {
      await ensureDemoSession();
      const created = await createPersona(draft);
      router.push(ROUTES.personaMemories(created.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法保存这颗星星。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-10 sm:px-8 lg:px-10">
        <PageTitle
          className="mt-2"
          title="为TA创建专属星星"
        />

        <form onSubmit={handleSubmit} className="mt-7 grid gap-5 md:grid-cols-[0.95fr_1.05fr]">
          <StarPanel className="p-6 sm:p-8">
            <h2 className="font-serif text-2xl font-bold text-starGold">TA的资料卡片</h2>
            <div className="mt-7 grid gap-5">
              <StarInput label="姓名">
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  className="star-input"
                  placeholder="请输入姓名"
                />
              </StarInput>

              <StarInput label="与我的关系">
                <select
                  value={relationship}
                  onChange={(event) => setRelationship(event.target.value)}
                  className="star-input"
                >
                  <option value="">选择你们的关系</option>
                  <option value="家人">家人</option>
                  <option value="朋友">朋友</option>
                  <option value="爱人">爱人</option>
                  <option value="老师">老师</option>
                </select>
              </StarInput>

              <StarInput label="TA对你的称谓">
                <input
                  value={nickname}
                  onChange={(event) => setNickname(event.target.value)}
                  className="star-input"
                  placeholder="例如：孩子、小铭、朋友"
                />
              </StarInput>

              <StarInput label="出生日期（可选）">
                <div className="relative">
                  <input
                    type="date"
                    value={birthDate}
                    onChange={(event) => setBirthDate(event.target.value)}
                    className="star-input pr-12"
                  />
                  <CalendarDays className="pointer-events-none absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 text-starMist/48" />
                </div>
              </StarInput>

              <div className="grid gap-2 text-sm font-semibold text-starMist/78">
                性别
                <div className="flex flex-wrap gap-6">
                  <Radio label="男" checked={gender === "male"} onChange={() => setGender("male")} />
                  <Radio label="女" checked={gender === "female"} onChange={() => setGender("female")} />
                  <Radio
                    label="不明确"
                    checked={gender === "unknown"}
                    onChange={() => setGender("unknown")}
                  />
                </div>
              </div>

              <div className="grid gap-2 text-sm font-semibold text-starMist/78">
                TA的状态
                <div className="flex flex-wrap gap-6">
                  <Radio
                    label="已离开"
                    checked={status === "deceased"}
                    onChange={() => setStatus("deceased")}
                  />
                  <Radio
                    label="陪伴中"
                    checked={status === "living"}
                    onChange={() => setStatus("living")}
                  />
                  <Radio label="其他" checked={status === "other"} onChange={() => setStatus("other")} />
                </div>
              </div>

              <StarInput label="想对TA说的话（选填）">
                <div className="relative">
                  <textarea
                    value={message}
                    onChange={(event) => setMessage(event.target.value.slice(0, 200))}
                    className="star-input min-h-24 resize-none pb-8"
                    placeholder="写下你想对TA说的话..."
                  />
                  <span className="absolute bottom-3 right-4 text-xs text-starMist/46">
                    {message.length}/200
                  </span>
                </div>
              </StarInput>
            </div>
          </StarPanel>

          <StarPanel className="p-6 sm:p-8">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-serif text-2xl font-bold text-starGold">上传珍贵回忆</h2>
              <span className="text-sm font-semibold text-starMist/54">
                <TwinkleLabel>越多回忆，星星越明亮</TwinkleLabel>
              </span>
            </div>
            <div className="mt-7 grid gap-4 sm:grid-cols-2">
              <UploadTile
                kind="照片"
                label="上传照片"
                icon={ImageIcon}
                count={uploads["照片"]}
                accept="image/*"
                onPick={(count) => setUploads((current) => ({ ...current, 照片: count }))}
              />
              <UploadTile
                kind="视频"
                label="上传视频"
                icon={Video}
                count={uploads["视频"]}
                accept="video/*"
                onPick={(count) => setUploads((current) => ({ ...current, 视频: count }))}
              />
              <UploadTile
                kind="声音"
                label="上传音频"
                icon={Mic}
                count={uploads["声音"]}
                accept="audio/*"
                onPick={(count) => setUploads((current) => ({ ...current, 声音: count }))}
              />
              <UploadTile
                kind="文字"
                label="记录文字"
                icon={FileText}
                count={uploads["文字"]}
                accept=".txt,.md,.doc,.docx"
                onPick={(count) => setUploads((current) => ({ ...current, 文字: count }))}
              />
            </div>
            <p className="mt-6 text-sm font-semibold leading-7 text-starMist/58">
              文件内容严格保密，仅您可见
            </p>
          </StarPanel>

          <div className="md:col-span-2">
            {error ? (
              <p className="mb-4 rounded-2xl border border-rose-300/20 bg-rose-500/15 p-4 text-center text-sm font-semibold text-rose-100">
                {error}
              </p>
            ) : null}
            <div className="flex justify-center">
              <StarButton type="submit" disabled={isSubmitting} className="w-full max-w-sm text-xl">
                {isSubmitting ? "正在保存星星..." : "保存这颗星星"}
                <Sparkles className="ml-3 h-5 w-5" />
              </StarButton>
            </div>
            <p className="mt-3 text-center text-xs font-semibold text-starMist/42">
              保存后可继续补充和修改，让这颗星星更完整。
            </p>
          </div>
        </form>
      </main>
    </StarShell>
  );
}

function Radio({
  label,
  checked,
  onChange
}: {
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 text-starMist/72">
      <input type="radio" checked={checked} onChange={onChange} className="h-4 w-4 accent-starGold" />
      {label}
    </label>
  );
}

function UploadTile({
  kind,
  label,
  icon: Icon,
  count,
  accept,
  onPick
}: {
  kind: UploadKind;
  label: string;
  icon: typeof ImageIcon;
  count: number;
  accept: string;
  onPick: (count: number) => void;
}) {
  return (
    <label className="grid min-h-[8.6rem] cursor-pointer place-items-center rounded-2xl border border-dashed border-starGold/20 bg-indigo-950/18 p-5 text-center transition hover:border-starGold/50 hover:bg-indigo-900/24">
      <input
        type="file"
        accept={accept}
        multiple
        className="sr-only"
        onChange={(event) => onPick(event.target.files?.length ?? 0)}
      />
      <span className="grid h-14 w-14 place-items-center rounded-2xl bg-violet-400/22 text-violet-200 shadow-[0_0_30px_rgba(181,128,255,0.35)]">
        <Icon className="h-8 w-8" />
      </span>
      <span className="mt-3 block text-lg font-bold text-starCream">{kind}</span>
      <span className="block text-sm font-semibold text-starMist/52">
        {count > 0 ? `已选择 ${count} 个文件` : label}
      </span>
    </label>
  );
}
