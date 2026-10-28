/// Extracts the port from the line the engine prints when it starts:
/// `apkguard bridge listening on http://127.0.0.1:33279`.
pub fn parse_port(line: &str) -> Option<u16> {
    line.split("http://127.0.0.1:").nth(1)?.trim().parse().ok()
}

#[cfg(test)]
mod tests {
    use super::parse_port;

    #[test]
    fn reads_the_port_from_the_startup_line() {
        assert_eq!(
            parse_port("apkguard bridge listening on http://127.0.0.1:33279\n"),
            Some(33279)
        );
    }

    #[test]
    fn ignores_other_output() {
        assert_eq!(parse_port("warming up"), None);
        assert_eq!(parse_port("listening on http://127.0.0.1:notaport"), None);
        assert_eq!(parse_port("http://127.0.0.1:99999"), None); // out of u16 range
        assert_eq!(parse_port(""), None);
    }
}
