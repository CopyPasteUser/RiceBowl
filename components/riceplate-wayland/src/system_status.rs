//! Bounded, unprivileged NetworkManager/WirePlumber status sampling.
//! These commands run only in an opt-in native session's worker thread.
//! Missing services report unavailable; a recipe never controls arguments.

use std::{io::Read, process::{Command, Stdio}, thread, time::{Duration, Instant}};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Network {
    Global,
    Local,
    Connecting,
    Offline,
    Unavailable,
}

impl Network {
    pub fn label(&self) -> &'static str {
        match self {
            Self::Global => "Net",
            Self::Local => "Local",
            Self::Connecting => "Wait",
            Self::Offline => "Off",
            Self::Unavailable => "N/A",
        }
    }

    fn parse(output: &str) -> Self {
        let output = output.trim().to_ascii_lowercase();
        match output.as_str() {
            "connected" | "connected (global)" => Self::Global,
            "connected (site only)" | "connected (local only)" => Self::Local,
            "connecting" => Self::Connecting,
            "disconnected" | "disconnecting" | "asleep" => Self::Offline,
            _ => Self::Unavailable,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Audio {
    Volume(u16),
    Muted,
    Unavailable,
}

impl Audio {
    pub fn label(&self) -> String {
        match self {
            Self::Volume(value) => format!("{value}%"),
            Self::Muted => "Mute".into(),
            Self::Unavailable => "N/A".into(),
        }
    }

    fn parse(output: &str) -> Self {
        let Some(value) = output.trim().strip_prefix("Volume: ") else {
            return Self::Unavailable;
        };
        let Some(number) = value.split_whitespace().next()
            .and_then(|value| value.parse::<f64>().ok()) else {
            return Self::Unavailable;
        };
        if !number.is_finite() || !(0.0..=1.5).contains(&number) {
            return Self::Unavailable;
        }
        if value.contains("[MUTED]") { return Self::Muted; }
        Self::Volume((number * 100.0).round() as u16)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SystemStatus {
    pub network: Network,
    pub audio: Audio,
}

impl Default for SystemStatus {
    fn default() -> Self {
        Self { network: Network::Unavailable, audio: Audio::Unavailable }
    }
}

impl SystemStatus {
    pub fn read(include_network: bool, include_audio: bool) -> Self {
        Self {
            network: if include_network {
                command_output("nmcli", &["--wait", "1", "-t", "-f", "STATE", "general"])
                    .map(|output| Network::parse(&output)).unwrap_or(Network::Unavailable)
            } else { Network::Unavailable },
            audio: if include_audio {
                command_output("wpctl", &["get-volume", "@DEFAULT_AUDIO_SINK@"])
                    .map(|output| Audio::parse(&output)).unwrap_or(Audio::Unavailable)
            } else { Audio::Unavailable },
        }
    }
}

fn command_output(program: &str, args: &[&str]) -> Option<String> {
    let mut child = Command::new(program).args(args).env("LC_ALL", "C")
        .stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::null())
        .spawn().ok()?;
    let started = Instant::now();
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) if started.elapsed() < Duration::from_millis(1200) => {
                thread::sleep(Duration::from_millis(15));
            }
            _ => {
                let _ = child.kill();
                let _ = child.wait();
                return None;
            }
        }
    };
    if !status.success() { return None; }
    let mut output = String::new();
    child.stdout.take()?.take(1024).read_to_string(&mut output).ok()?;
    Some(output)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn network_cli_states_do_not_fabricate_internet_connectivity() {
        assert_eq!(Network::parse("connected\n"), Network::Global);
        assert_eq!(Network::parse("connected (site only)"), Network::Local);
        assert_eq!(Network::parse("connecting\n"), Network::Connecting);
        assert_eq!(Network::parse("disconnected\n"), Network::Offline);
        assert_eq!(Network::parse("garbage"), Network::Unavailable);
        assert_eq!(Network::Unavailable.label(), "N/A");
    }

    #[test]
    fn pipewire_volume_parsing_bounds_and_mute_are_explicit() {
        assert_eq!(Audio::parse("Volume: 0.58\n"), Audio::Volume(58));
        assert_eq!(Audio::parse("Volume: 0.20 [MUTED]\n"), Audio::Muted);
        assert_eq!(Audio::parse("Volume: 1.15"), Audio::Volume(115));
        for invalid in ["", "Volume: nan", "Volume: -2", "Volume: 12", "garbage"] {
            assert_eq!(Audio::parse(invalid), Audio::Unavailable);
        }
    }
}
