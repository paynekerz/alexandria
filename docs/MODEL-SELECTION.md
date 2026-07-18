# How Alexandria handles your model choice

During setup, Alexandria asks which Claude model should do the teaching. This page explains, honestly, what that choice can and cannot control.

## The limitation, stated plainly

**A skill cannot switch the model.** When you invoke `alexandria-teach`, it runs on whatever model your Claude Code session is already using. A skill is a set of instructions loaded into that model; it has no button to swap the model out, and nothing we write in the skill can change that. Any tool that claims its skill "runs on model X" without further mechanism is overstating what skills can do.

## What actually enforces your preference: the teacher subagent

Claude Code has one real mechanism for pinning a model: **subagents**. A subagent is a helper with its own configuration file, and that file can name the model it runs on. Claude Code honors that line every time the subagent is used.

So Alexandria splits the work:

- Your main session (any model) handles the conversation: figuring out what you asked, checking your library, offering the save.
- The heavy explanation work goes to the **`alexandria-teacher` subagent**, whose config file contains `model: <your choice>`.

During setup, `scripts/setup.py` takes the template at `agents/alexandria-teacher.md`, replaces its model placeholder with the model you chose, and installs it to `~/.claude/agents/`. From then on, every lesson's explanation runs on your chosen model, regardless of what model your session happens to be using.

If you chose `inherit` at setup, the model line is omitted entirely and the teacher runs on whatever your session runs on.

To change your choice later: edit `preferredModel` in `~/.alexandria/config.json` and the `model:` line in `~/.claude/agents/alexandria-teacher.md`, keeping them in sync. (Re-running `setup.py --force` re-fills the model line only when the installed agent file still contains the template placeholder; after first install, editing the `model:` line directly is the reliable path.)

## Outside the subagent: recommendation only

Anywhere the subagent isn't doing the work -- the conversational parts of a lesson, or any future environment without subagent support -- Alexandria **cannot** enforce your preference. The most it can do is notice that your session model differs from your configured preference and say so, recommending you run `/model` to switch. Whether you do is up to you; nothing happens automatically. We say "recommend" because that is all it is.
