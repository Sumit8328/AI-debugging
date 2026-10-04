import React, { useState } from "react";
import { FolderTree, FileCode, CheckSquare, Upload, Terminal } from "lucide-react";

export function CodebasePanel({ demos = [], selectedDemoId, onSelectDemo, testCommand }) {
  const [selectedFile, setSelectedFile] = useState("processor.py");

  // Sample code snippets for demo projects
  const fileSnippets = {
    "processor.py": `def slice_batch(items, batch_size):
    """
    Slices an iterable of items into chunks of size batch_size.
    BUG: Loops up to len(items) + 1 which causes out of bounds / overflow.
    """
    batches = []
    # BUG: + 1 causes index boundary spillover
    for i in range(0, len(items) + 1, batch_size):
        batches.append(items[i:i + batch_size])
    return batches`,
    "test_processor.py": `import pytest
from processor import slice_batch

def test_standard_batch():
    assert slice_batch([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

def test_boundary_exact_match():
    assert slice_batch([1, 2, 3, 4, 5, 6], 3) == [[1, 2, 3], [4, 5, 6]]

def test_empty_input():
    assert slice_batch([], 2) == []

def test_zero_or_negative_batch_size():
    with pytest.raises(ValueError):
        slice_batch([1, 2, 3], batch_size=0)`
  };

  return (
    <div className="flex flex-col h-full bg-[#0c0e18] border border-[#1d2235] rounded-xl overflow-hidden shadow-2xl">
      {/* Header & Demo Selector */}
      <div className="px-4 py-3 bg-[#111524] border-b border-[#1d2235]">
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-2">
            <FolderTree className="w-5 h-5 text-zinc-300" />
            <span className="text-sm font-bold tracking-wider uppercase text-zinc-100 font-mono">
              Codebase & Tests
            </span>
          </div>
          <button
            onClick={() => alert("ZIP upload will be fully connected in Phase 2. Preset demos are ready below.")}
            className="text-xs px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 flex items-center gap-1.5 transition-colors font-mono cursor-pointer"
          >
            <Upload className="w-3.5 h-3.5" /> Upload ZIP
          </button>
        </div>

        {/* Demo Switcher */}
        <div className="space-y-1.5">
          <label className="text-xs text-zinc-300 font-mono uppercase tracking-wider block font-semibold">
            Target Bug Demo:
          </label>
          <div className="grid grid-cols-3 gap-1.5">
            {demos.map((d) => (
              <button
                key={d.id}
                onClick={() => onSelectDemo(d)}
                className={`text-[13px] py-1.5 px-2 rounded-md text-center truncate font-mono border transition-all cursor-pointer ${
                  selectedDemoId === d.id
                    ? "bg-zinc-700 border-zinc-500 text-white font-bold shadow-md"
                    : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                }`}
                title={d.title}
              >
                {d.id}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Target Test Command Badge */}
      <div className="px-4 py-2 bg-[#090b12] border-b border-[#1d2235] flex items-center justify-between text-sm font-mono">
        <span className="text-zinc-400 flex items-center gap-1.5">
          <Terminal className="w-4 h-4 text-zinc-400" /> Target:
        </span>
        <span className="text-emerald-400 font-bold bg-emerald-950/60 px-2.5 py-0.5 rounded border border-emerald-800/60 text-sm">
          {testCommand || "pytest"}
        </span>
      </div>

      {/* File Tree Tabs */}
      <div className="p-2.5 border-b border-[#1d2235] bg-[#0e111d] flex gap-2">
        {["processor.py", "test_processor.py"].map((file) => {
          const isTest = file.startsWith("test_");
          return (
            <button
              key={file}
              onClick={() => setSelectedFile(file)}
              className={`flex-1 flex items-center justify-center gap-2 py-1.5 px-3 rounded-md text-[14px] font-mono font-medium border transition-colors cursor-pointer ${
                selectedFile === file
                  ? "bg-zinc-800 border-zinc-600 text-zinc-100 font-bold shadow"
                  : "bg-black/40 border-transparent text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {isTest ? <CheckSquare className="w-4 h-4 text-emerald-400" /> : <FileCode className="w-4 h-4 text-sky-400" />}
              {file}
            </button>
          );
        })}
      </div>

      {/* Code Viewer */}
      <div className="flex-1 p-4 bg-[#08090f] font-mono text-[14px] overflow-auto leading-relaxed">
        <div className="text-xs text-zinc-400 mb-2 flex items-center justify-between pb-1.5 border-b border-zinc-800">
          <span className="font-semibold text-zinc-200">{selectedFile}</span>
          <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">READ-ONLY REPO VIEW</span>
        </div>
        <pre className="text-zinc-200 leading-relaxed font-mono">
          <code>
            {(fileSnippets[selectedFile] || "// File content loading...").split("\n").map((line, i) => (
              <div key={i} className="table-row">
                <span className="table-cell text-zinc-500 text-[13px] pr-4 select-none text-right font-mono">
                  {i + 1}
                </span>
                <span className="table-cell">{line}</span>
              </div>
            ))}
          </code>
        </pre>
      </div>
    </div>
  );
}
export default CodebasePanel;
