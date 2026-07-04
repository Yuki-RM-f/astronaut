"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import {
  CalendarDays,
  CheckCircle2,
  FileText,
  ImageIcon,
  Mic,
  Sparkles,
  Video
} from "lucide-react";
import {
  PageTitle,
  StarButton,
  StarInput,
  StarNav,
  StarPanel,
  StarShell,
  TwinkleLabel
} from "@/src/components/StarSite";
import { UploadMemoryTile } from "@/src/components/UploadMemoryTile";
import { ensureDemoSession } from "@/src/lib/auth";
import {
  buildCreatePersonaProgress,
  buildCreatePersonaShortBio,
  createPersona,
  type CreatePersonaProcessingStage,
  type PersonaDraft
} from "@/src/lib/persona";
import { describeSelectedUploadFiles, uploadMaterials } from "@/src/lib/materials";
import { ROUTES } from "@/src/lib/routes";

type UploadKind = "照片" | "视频" | "声音" | "文字";

const CREATION_STEPS = ["资料卡片", "上传回忆", "保存并进入审核"] as const;

export default function NewPersonaPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [relationship, setRelationship] = useState("");
  const [nickname, setNickname] = useState("");
  const [age, setAge] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [gender, setGender] = useState<"male" | "female" | "unknown">("male");
  const [status, setStatus] = useState<"deceased" | "living" | "other">("deceased");
  const [message, setMessage] = useState("");
  const [uploads, setUploads] = useState<Record<UploadKind, File[]>>({
    照片: [],
    视频: [],
    声音: [],
    文字: []
  });
  const [error, setError] = useState<string | null>(null);
  const [uploadRecoveryPersonaId, setUploadRecoveryPersonaId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [processingStage, setProcessingStage] = useState<CreatePersonaProcessingStage | null>(null);
  const selectedUploadFiles = describeSelectedUploadFiles(uploads);
  const processingProgress = processingStage
    ? buildCreatePersonaProgress(processingStage, selectedUploadFiles.length)
    : null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setUploadRecoveryPersonaId(null);
    setProcessingStage(null);

    if (!name.trim() || !relationship.trim() || !nickname.trim() || !isValidAge(age)) {
      setError("请至少填写姓名、TA 是我的、TA 对你的称谓和 1-150 之间的年龄/享年。");
      return;
    }

    const personaType = status === "living" ? "living_relative" : status === "other" ? "fictional_character" : "deceased_relative";
    const personaStatus = status === "living" ? "living" : status === "other" ? "fictional" : "deceased";
    const draft: PersonaDraft = {
      name,
      persona_type: personaType,
      status: personaStatus,
      relationship_to_user: relationship,
      user_nickname_by_persona: nickname,
      age,
      gender,
      short_bio: buildCreatePersonaShortBio({ birthDate, message })
    };

    setIsSubmitting(true);
    try {
      setProcessingStage("demo_session");
      await ensureDemoSession();
      setProcessingStage("persona_card");
      const created = await createPersona(draft);
      const files = Object.values(uploads).flat();
      if (files.length > 0) {
        setProcessingStage("upload_memories");
        try {
          await uploadMaterials(created.id, {
            files
          });
        } catch {
          setUploadRecoveryPersonaId(created.id);
          setError("星星已保存，但资料上传失败。请进入资料上传页继续补传。");
          setProcessingStage(null);
          return;
        }
      }
      setProcessingStage("review_entry");
      router.push(ROUTES.personaUploads(created.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法保存这颗星星。");
      setProcessingStage(null);
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

        <CreationStepStrip />

        <form onSubmit={handleSubmit} className="mt-7 grid gap-5 pb-32 md:grid-cols-[0.95fr_1.05fr] md:pb-0">
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

              <StarInput label="TA是我的">
                <input
                  value={relationship}
                  onChange={(event) => setRelationship(event.target.value)}
                  className="star-input"
                  placeholder="例如：妈妈、外婆、朋友、老师"
                />
              </StarInput>

              <StarInput label="TA对你的称谓">
                <input
                  value={nickname}
                  onChange={(event) => setNickname(event.target.value)}
                  className="star-input"
                  placeholder="例如：孩子、小铭、朋友"
                />
              </StarInput>

              <StarInput label="年龄/享年">
                <input
                  type="number"
                  min="1"
                  max="150"
                  value={age}
                  onChange={(event) => setAge(event.target.value)}
                  className="star-input"
                  placeholder="例如：72"
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

              <StarInput label="有关TA的一切都可以写在这里">
                <div className="relative">
                  <textarea
                    value={message}
                    onChange={(event) => setMessage(event.target.value.slice(0, 200))}
                    className="star-input min-h-24 resize-none pb-8"
                    placeholder="TA的兴趣爱好、性格特征等"
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
              <UploadMemoryTile
                kind="照片"
                label="上传照片"
                icon={ImageIcon}
                count={uploads["照片"].length}
                accept="image/*"
                onPick={(files) => setUploads((current) => ({ ...current, 照片: files }))}
              />
              <UploadMemoryTile
                kind="视频"
                label="上传视频"
                icon={Video}
                count={uploads["视频"].length}
                accept="video/*"
                onPick={(files) => setUploads((current) => ({ ...current, 视频: files }))}
              />
              <UploadMemoryTile
                kind="声音"
                label="上传音频"
                icon={Mic}
                count={uploads["声音"].length}
                accept="audio/*"
                onPick={(files) => setUploads((current) => ({ ...current, 声音: files }))}
              />
              <UploadMemoryTile
                kind="文字"
                label="记录文字"
                icon={FileText}
                count={uploads["文字"].length}
                accept=".txt,.md,.doc,.docx"
                onPick={(files) => setUploads((current) => ({ ...current, 文字: files }))}
              />
            </div>
            {selectedUploadFiles.length > 0 ? (
              <div className="mt-6 rounded-2xl border border-starGold/14 bg-indigo-950/24 p-4">
                <h3 className="text-sm font-bold text-starGold">已选择待上传的回忆</h3>
                <ul className="mt-3 grid gap-2">
                  {selectedUploadFiles.map((file, index) => (
                    <li
                      key={`${file.kind}-${file.name}-${index}`}
                      className="grid gap-2 rounded-xl border border-white/8 bg-white/[0.04] px-3 py-3 text-sm sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center"
                    >
                      <span className="w-fit rounded-full border border-starGold/18 bg-starGold/10 px-3 py-1 text-xs font-bold text-starGold">
                        {file.kind}
                      </span>
                      <span className="min-w-0 break-all font-semibold text-starCream">
                        {file.name}
                      </span>
                      <span className="text-xs font-semibold text-starMist/54 sm:text-right">
                        {file.typeLabel} · {file.sizeLabel}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <p className="mt-6 text-sm font-semibold leading-7 text-starMist/58">
              文件内容严格保密，仅您可见
            </p>
          </StarPanel>

          <div className="fixed inset-x-4 bottom-4 z-40 rounded-[1.5rem] border border-white/10 bg-indigo-950/88 p-4 shadow-[0_-18px_52px_rgba(0,0,0,0.28)] backdrop-blur md:static md:col-span-2 md:rounded-none md:border-0 md:bg-transparent md:p-0 md:shadow-none md:backdrop-blur-0">
            {error ? (
              <div className="mb-4 rounded-2xl border border-rose-300/20 bg-rose-500/15 p-4 text-center text-sm font-semibold text-rose-100">
                {error}
                {uploadRecoveryPersonaId ? (
                  <button
                    type="button"
                    onClick={() => router.push(ROUTES.personaUploads(uploadRecoveryPersonaId))}
                    className="ml-2 underline underline-offset-4"
                  >
                    去补传资料
                  </button>
                ) : null}
              </div>
            ) : null}
            <div className="flex justify-center">
              <StarButton type="submit" disabled={isSubmitting} className="w-full max-w-sm text-xl">
                {isSubmitting ? "正在保存星星..." : "保存这颗星星"}
                <Sparkles className="ml-3 h-5 w-5" />
              </StarButton>
            </div>
            {processingProgress ? (
              <div className="mx-auto mt-4 w-full max-w-xl" aria-live="polite">
                <div className="h-3 overflow-hidden rounded-full border border-starGold/24 bg-indigo-950/48 shadow-inner shadow-black/20">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-starGold via-amber-200 to-starGold transition-[width] duration-300 ease-out"
                    role="progressbar"
                    aria-label="保存星星进度"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={processingProgress.percent}
                    aria-valuetext={processingProgress.label}
                    style={{ width: `${processingProgress.percent}%` }}
                  />
                </div>
                <p className="mt-2 text-center text-sm font-semibold text-starMist/66">
                  {processingProgress.label}
                </p>
              </div>
            ) : null}
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

function CreationStepStrip() {
  return (
    <section
      className="mx-auto mt-6 grid max-w-4xl gap-3 rounded-[1.4rem] border border-starGold/14 bg-indigo-950/28 p-3 shadow-[0_12px_34px_rgba(0,0,0,0.18)] sm:grid-cols-3"
      aria-label="创建档案流程"
    >
      {CREATION_STEPS.map((step, index) => (
        <div key={step} className="flex items-center gap-3 rounded-2xl bg-white/[0.04] px-4 py-3">
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-starGold/14 text-starGold">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
          </span>
          <span>
            <span className="block text-xs font-black tracking-[0.12em] text-starGold/78">
              STEP {index + 1}
            </span>
            <span className="block text-sm font-bold text-starCream">{step}</span>
          </span>
        </div>
      ))}
    </section>
  );
}

function isValidAge(value: string): boolean {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 1 && parsed <= 150;
}
