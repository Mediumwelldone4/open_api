"use client";

import React, { useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from "recharts";

import type { IngestionSummary } from "./connection-wizard";
import type { VisualizationPreset } from "./visualization-presets";

const COLORS = ["#38bdf8", "#22c55e", "#f97316", "#a855f7", "#facc15"];

const isNumeric = (value: unknown): value is number => typeof value === "number";

const parseDate = (value: unknown): Date | null => {
  if (typeof value !== "string") return null;
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return null;
  return new Date(parsed);
};

type VisualizationPreviewProps = {
  summary: IngestionSummary | null;
  preset: VisualizationPreset;
};

export function VisualizationPreview({ summary, preset }: VisualizationPreviewProps) {
  const chart = useMemo(() => {
    if (!summary) return null;
    const [field] = preset.fields;

    if (preset.type === "numeric" && field) {
      const data = summary.sample_records
        .map((record, index) => {
          const raw = record[field];
          const value = typeof raw === "string" ? Number(raw) : raw;
          if (!isNumeric(value) || Number.isNaN(value)) {
            return null;
          }
          return { index, value };
        })
        .filter((item): item is { index: number; value: number } => item !== null);

      if (data.length < 2) return null;

      return (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
            <XAxis dataKey="index" stroke="rgba(148,163,184,0.8)" tickLine={false} />
            <YAxis stroke="rgba(148,163,184,0.8)" tickLine={false} width={50} />
            <Tooltip cursor={{ stroke: "#38bdf8", strokeWidth: 1 }} />
            <Line type="monotone" dataKey="value" stroke="#38bdf8" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      );
    }

    if (preset.type === "categorical") {
      const counts = new Map<string, number>();
      summary.sample_records.forEach((record) => {
        const label = preset.fields
          .map((fieldName) => record[fieldName])
          .filter((value) => typeof value === "string")
          .join(" · ");
        if (!label) return;
        counts.set(label, (counts.get(label) ?? 0) + 1);
      });

      const data = Array.from(counts.entries()).map(([name, value]) => ({ name, value }));
      if (data.length === 0) return null;

      if (data.length <= 5) {
        return (
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" outerRadius={90} label>
                {data.map((entry, index) => (
                  <Cell key={`slice-${entry.name}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        );
      }

      return (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} layout="vertical" margin={{ left: 60, top: 10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
            <XAxis type="number" stroke="rgba(148,163,184,0.8)" tickLine={false} />
            <YAxis dataKey="name" type="category" width={120} stroke="rgba(148,163,184,0.8)" />
            <Tooltip />
            <Bar dataKey="value" fill="#38bdf8" radius={[4, 4, 4, 4]} />
          </BarChart>
        </ResponsiveContainer>
      );
    }

    if (preset.type === "timeseries" && field) {
      const data = summary.sample_records
        .map((record) => {
          const date = parseDate(record[field]);
          const numericFields = Object.entries(record)
            .filter(([, value]) => isNumeric(value))
            .map(([key, value]) => [key, value as number] as const);
          if (!date || numericFields.length === 0) return null;
          const numericValues = numericFields.reduce<Record<string, number>>((acc, [key, value]) => {
            acc[key] = value;
            return acc;
          }, {});
          return {
            date,
            ...numericValues,
          } as { date: Date } & Record<string, number>;
        })
        .filter((item): item is { date: Date } & Record<string, number> => item !== null)
        .sort((a, b) => (a.date as Date).getTime() - (b.date as Date).getTime())
        .map((item) => ({ ...item, dateLabel: (item.date as Date).toLocaleString() }));

      const numericKeys = summary.schema_fields.filter((key) =>
        data.some((item) => {
          const record = item as Record<string, unknown>;
          return isNumeric(record[key]);
        })
      );

      if (data.length < 2 || numericKeys.length === 0) return null;

      return (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
            <XAxis dataKey="dateLabel" stroke="rgba(148,163,184,0.8)" tickLine={false} minTickGap={30} />
            <YAxis stroke="rgba(148,163,184,0.8)" tickLine={false} width={50} />
            <Tooltip />
            {numericKeys.slice(0, 3).map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      );
    }

    return null;
  }, [preset, summary]);

  if (!chart) {
    return <p className="muted">Not enough data to generate a visualization.</p>;
  }

  return <div className="chart-preview">{chart}</div>;
}
