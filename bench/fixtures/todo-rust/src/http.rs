//! A small HTTP/1.1 reader and writer, enough for one page and one form.

use std::collections::HashMap;
use std::io::{self, BufRead, BufReader, Read, Write};

pub struct Request {
    pub method: String,
    pub path: String,
    pub query: String,
    pub headers: HashMap<String, String>,
    pub body: String,
}

impl Request {
    /// A request with no headers, for tests and for callers that build one by hand.
    pub fn new(method: &str, target: &str, body: &str) -> Request {
        let (path, query) = split_target(target);
        Request { method: method.to_string(), path, query, headers: HashMap::new(), body: body.to_string() }
    }
}

pub struct Response {
    pub status: u16,
    pub content_type: &'static str,
    pub location: Option<String>,
    pub body: String,
}

impl Response {
    pub fn html(status: u16, body: String) -> Response {
        Response { status, content_type: "text/html; charset=utf-8", location: None, body }
    }

    pub fn text(status: u16, body: &str) -> Response {
        Response { status, content_type: "text/plain; charset=utf-8", location: None, body: format!("{}\n", body) }
    }

    pub fn redirect(location: &str) -> Response {
        Response { status: 303, content_type: "text/plain; charset=utf-8", location: Some(location.to_string()), body: String::new() }
    }

    pub fn write_to(&self, out: &mut impl Write) -> io::Result<()> {
        let reason = match self.status {
            200 => "OK",
            303 => "See Other",
            400 => "Bad Request",
            404 => "Not Found",
            _ => "Internal Server Error",
        };
        write!(out, "HTTP/1.1 {} {}\r\n", self.status, reason)?;
        write!(out, "Content-Type: {}\r\n", self.content_type)?;
        if let Some(location) = &self.location {
            write!(out, "Location: {}\r\n", location)?;
        }
        write!(out, "Content-Length: {}\r\nConnection: close\r\n\r\n{}", self.body.len(), self.body)?;
        out.flush()
    }
}

/// Reads one request: the request line, the headers, and a body of Content-Length bytes.
pub fn read_request(stream: &mut impl Read) -> io::Result<Request> {
    let mut reader = BufReader::new(stream);
    let mut line = String::new();
    reader.read_line(&mut line)?;
    let mut parts = line.split_whitespace();
    let (Some(method), Some(target)) = (parts.next(), parts.next()) else {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "no request line"));
    };
    let (path, query) = split_target(target);
    let method = method.to_string();
    let mut headers = HashMap::new();
    loop {
        let mut header = String::new();
        if reader.read_line(&mut header)? == 0 || header.trim().is_empty() {
            break;
        }
        if let Some((name, value)) = header.split_once(':') {
            headers.insert(name.trim().to_ascii_lowercase(), value.trim().to_string());
        }
    }
    let length: usize = headers.get("content-length").and_then(|v| v.parse().ok()).unwrap_or(0);
    let mut body = vec![0; length];
    reader.read_exact(&mut body)?;
    Ok(Request { method, path, query, headers, body: String::from_utf8_lossy(&body).into_owned() })
}

fn split_target(target: &str) -> (String, String) {
    match target.split_once('?') {
        Some((path, query)) => (path.to_string(), query.to_string()),
        None => (target.to_string(), String::new()),
    }
}

/// The decoded value of one field of a form body (application/x-www-form-urlencoded).
pub fn form_value(body: &str, name: &str) -> Option<String> {
    body.split('&').find_map(|pair| {
        let (key, value) = pair.split_once('=').unwrap_or((pair, ""));
        (decode(key) == name).then(|| decode(value))
    })
}

fn decode(text: &str) -> String {
    let bytes = text.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        match bytes[i] {
            b'+' => out.push(b' '),
            b'%' if i + 2 < bytes.len() => match (hex(bytes[i + 1]), hex(bytes[i + 2])) {
                (Some(high), Some(low)) => {
                    out.push(high * 16 + low);
                    i += 2;
                }
                _ => out.push(b'%'),
            },
            byte => out.push(byte),
        }
        i += 1;
    }
    String::from_utf8_lossy(&out).into_owned()
}

fn hex(byte: u8) -> Option<u8> {
    (byte as char).to_digit(16).map(|digit| digit as u8)
}
