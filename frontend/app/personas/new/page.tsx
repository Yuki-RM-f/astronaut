"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { Camera, Heart, PenLine, ShieldCheck } from "lucide-react";
import { DemoEntry } from "@/src/components/DemoEntry";
import {
  GlassPanel,
  MemoryContainer,
  MemoryShell,
  MemoryTitle,
  PaperNote,
  StepRibbon
} from "@/src/components/MemorySpace";
import { getAuthToken } from "@/src/lib/auth";
import {
  createPersona,
  defaultStatusForType,
  PERSONA_GENDER_OPTIONS,
  PERSONA_STATUS_OPTIONS,
  PERSONA_TYPE_OPTIONS,
  PersonaDraft,
  PersonaType,
  validatePersonaDraft
} from "@/src/lib/persona";
import { ROUTES } from "@/src/lib/routes";

const FIELD_LABELS: Record<keyof PersonaDraft, string> = {
  name: "人物姓名",
  persona_type: "人物类型",
  status: "当前状态",
  relationship_to_user: "你们的关系",
  user_nickname_by_persona: "TA 对你的称呼",
  gender: "性别",
  language: "主要语言",
  short_bio: "简短介绍",
  speaking_style: "说话风格",
  emotional_style: "情绪方式",
  forbidden_expressions: "禁止表达"
};

const INITIAL_DRAFT: PersonaDraft = {
  name: "",
  persona_type: "deceased_relative",
  status: "deceased",
  relationship_to_user: "",
  user_nickname_by_persona: "",
  gender: "unknown",
  language: "zh-CN",
  short_bio: "",
  speaking_style: "",
  emotional_style: "",
  forbidden_expressions: ""
};

export default function NewPersonaPage() {
  const router = useRouter();
  const [draft, setDraft] = useState<PersonaDraft>(INITIAL_DRAFT);
  const [missingFields, setMissingFields] = useState<Array<keyof PersonaDraft>>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasToken, setHasToken] = useState(true);

  useEffect(() => {
    setHasToken(Boolean(getAuthToken()));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!getAuthToken()) {
      setHasToken(false);
      setError("请先登录，或使用免注册演示入口。");
      return;
    }

    const validation = validatePersonaDraft(draft);
    setMissingFields(validation.missingFields);

    if (!validation.ok) {
      setError("请补全人物创建所需信息。");
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await createPersona(draft);
      router.push(ROUTES.personaDetail(created.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法创建人物。");
    } finally {
      setIsSubmitting(false);
    }
  }

  function updateField(field: keyof PersonaDraft, value: string) {
    setDraft((current) => ({
      ...current,
      [field]: value
    }));
  }

  function updatePersonaType(event: ChangeEvent<HTMLSelectElement>) {
    const personaType = event.target.value as PersonaType;
    setDraft((current) => ({
      ...current,
      persona_type: personaType,
      status: defaultStatusForType(personaType)
    }));
  }

  function hasMissingField(field: keyof PersonaDraft): boolean {
    return missingFields.includes(field);
  }

  return (
    <MemoryShell background="familyLivingRoom">
      <MemoryContainer className="grid gap-8 lg:grid-cols-[0.86fr_1.14fr] lg:items-start">
        <aside className="lg:sticky lg:top-28">
          <Link href={ROUTES.dashboard} className="text-sm font-semibold text-memoryAccent">
            返回记忆空间
          </Link>
          <MemoryTitle
            className="mt-6"
            title="创建人物"
            subtitle="让珍贵的记忆被看见、被记得、被陪伴。先写下 TA 的信息和边界，后续资料整理会更准确。"
          />
          <PaperNote className="mt-8 max-w-md rotate-[-3deg]">
            <p className="font-serif text-lg leading-8">
              填写 TA 的信息，
              <br />
              上传珍贵的资料，
              <br />
              我们会帮你用心解析。
            </p>
          </PaperNote>
        </aside>

        <div className="grid gap-5">
          <StepRibbon activeIndex={0} />

          {!hasToken ? (
            <GlassPanel>
              <h2 className="text-xl font-semibold text-memoryText">
                无需注册也可以体验完整示例
              </h2>
              <p className="mt-2 text-sm leading-7 text-memoryText/70">
                如果只是想先体验，可以直接进入外婆示例记忆空间。
              </p>
              <div className="mt-5">
                <DemoEntry label="立即体验示例" />
              </div>
            </GlassPanel>
          ) : null}

          <form className="grid gap-5" onSubmit={handleSubmit}>
            <StepSection step="1" title="选择类型" icon={Heart}>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm font-semibold text-memoryText">
                  人物类型
                  <select
                    value={draft.persona_type}
                    onChange={updatePersonaType}
                    className={inputClass(hasMissingField("persona_type"))}
                  >
                    {PERSONA_TYPE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-2 text-sm font-semibold text-memoryText">
                  当前状态
                  <select
                    value={draft.status}
                    onChange={(event) => updateField("status", event.target.value)}
                    className={inputClass(hasMissingField("status"))}
                  >
                    {PERSONA_STATUS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </StepSection>

            <StepSection step="2" title="基础资料" icon={Camera}>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm font-semibold text-memoryText">
                  人物姓名
                  <input
                    value={draft.name}
                    onChange={(event) => updateField("name", event.target.value)}
                    className={inputClass(hasMissingField("name"))}
                    placeholder="外婆"
                  />
                </label>
                <label className="grid gap-2 text-sm font-semibold text-memoryText">
                  性别
                  <select
                    value={draft.gender}
                    onChange={(event) => updateField("gender", event.target.value)}
                    className={inputClass(hasMissingField("gender"))}
                  >
                    {PERSONA_GENDER_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-2 text-sm font-semibold text-memoryText">
                  主要语言
                  <input
                    value={draft.language}
                    onChange={(event) => updateField("language", event.target.value)}
                    className={inputClass(hasMissingField("language"))}
                    placeholder="zh-CN"
                  />
                </label>
                <TextAreaField
                  label="简短介绍"
                  value={draft.short_bio}
                  missing={hasMissingField("short_bio")}
                  onChange={(value) => updateField("short_bio", value)}
                  placeholder="用事实概括 TA 是谁，不要写无法确认的能力。"
                />
              </div>
            </StepSection>

            <StepSection step="3" title="关系称呼" icon={PenLine}>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm font-semibold text-memoryText">
                  你们的关系
                  <input
                    value={draft.relationship_to_user}
                    onChange={(event) => updateField("relationship_to_user", event.target.value)}
                    className={inputClass(hasMissingField("relationship_to_user"))}
                    placeholder="外婆"
                  />
                </label>
                <label className="grid gap-2 text-sm font-semibold text-memoryText">
                  TA 对你的称呼
                  <input
                    value={draft.user_nickname_by_persona}
                    onChange={(event) =>
                      updateField("user_nickname_by_persona", event.target.value)
                    }
                    className={inputClass(hasMissingField("user_nickname_by_persona"))}
                    placeholder="小铭"
                  />
                </label>
              </div>
            </StepSection>

            <StepSection step="4" title="说话风格与边界" icon={ShieldCheck}>
              <div className="grid gap-4 md:grid-cols-2">
                <TextAreaField
                  label="说话风格"
                  value={draft.speaking_style}
                  missing={hasMissingField("speaking_style")}
                  onChange={(value) => updateField("speaking_style", value)}
                  placeholder="温和、朴素，经常使用对你的称呼。"
                />
                <TextAreaField
                  label="情绪方式"
                  value={draft.emotional_style}
                  missing={hasMissingField("emotional_style")}
                  onChange={(value) => updateField("emotional_style", value)}
                  placeholder="安慰、鼓励，但不替用户做重大决定。"
                />
                <TextAreaField
                  label="禁止表达"
                  value={draft.forbidden_expressions}
                  missing={hasMissingField("forbidden_expressions")}
                  onChange={(value) => updateField("forbidden_expressions", value)}
                  placeholder="不要说「我真的回来了」；不要暗示自己是本人复生。"
                />
              </div>
            </StepSection>

            {error ? (
              <div className="rounded-2xl border border-red-200 bg-red-50/90 p-4 text-sm text-red-700 shadow-soft">
                <p>{error}</p>
                {missingFields.length > 0 ? (
                  <p className="mt-2">
                    缺少：{missingFields.map((field) => FIELD_LABELS[field]).join("、")}
                  </p>
                ) : null}
              </div>
            ) : null}

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={isSubmitting}
                className="memory-button rounded-2xl bg-memoryAccent px-5 py-3 text-sm font-semibold text-white shadow-warm transition hover:bg-memoryAccentDark focus:outline-none focus:ring-4 focus:ring-memoryAccent/25 disabled:cursor-not-allowed disabled:bg-memoryText/30"
              >
                {isSubmitting ? "正在创建..." : "创建人物并进入记忆空间"}
              </button>
              <Link
                href={ROUTES.dashboard}
                className="rounded-2xl border border-memoryLine/80 bg-white/72 px-5 py-3 text-sm font-semibold text-memoryText shadow-soft"
              >
                取消
              </Link>
            </div>
          </form>
        </div>
      </MemoryContainer>
    </MemoryShell>
  );
}

function StepSection({
  step,
  title,
  icon: Icon,
  children
}: {
  step: string;
  title: string;
  icon: typeof Heart;
  children: ReactNode;
}) {
  return (
    <GlassPanel>
      <div className="mb-5 flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-memoryAccent text-sm font-semibold text-white shadow-soft">
          {step}
        </span>
        <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-memoryWarm text-memoryAccent">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <h2 className="text-lg font-semibold text-memoryText">{title}</h2>
      </div>
      {children}
    </GlassPanel>
  );
}

function TextAreaField({
  label,
  value,
  missing,
  onChange,
  placeholder
}: {
  label: string;
  value: string;
  missing: boolean;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <label className="grid gap-2 text-sm font-semibold text-memoryText md:col-span-2">
      {label}
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={`${inputClass(missing)} min-h-28 resize-y`}
        placeholder={placeholder}
      />
    </label>
  );
}

function inputClass(hasError: boolean): string {
  const borderClass = hasError ? "border-red-400" : "border-memoryLine/80";
  return `rounded-2xl border ${borderClass} bg-white/74 px-4 py-3 text-sm text-memoryText outline-none transition focus:border-memoryAccent focus:ring-4 focus:ring-memoryAccent/20`;
}
