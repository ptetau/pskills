//! Item storage: the to-do items in a text file, one item on each line.
//!
//! Each line is `<id>` TAB `<text>`. A missing file holds no items.

use std::fs;
use std::io;
use std::path::PathBuf;

#[derive(Debug, Clone, PartialEq)]
pub struct Item {
    pub id: u64,
    pub text: String,
}

pub struct Store {
    path: PathBuf,
}

impl Store {
    pub fn new(path: impl Into<PathBuf>) -> Store {
        Store { path: path.into() }
    }

    /// Each item, in the order in which it was added.
    pub fn load(&self) -> io::Result<Vec<Item>> {
        let text = match fs::read_to_string(&self.path) {
            Ok(text) => text,
            Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(Vec::new()),
            Err(error) => return Err(error),
        };
        Ok(text
            .lines()
            .filter_map(|line| {
                let (id, text) = line.split_once('\t')?;
                Some(Item { id: id.parse().ok()?, text: text.to_string() })
            })
            .collect())
    }

    /// Adds an item with the next free id. Tabs and line breaks in the text become spaces.
    pub fn add(&self, text: &str) -> io::Result<Item> {
        let mut items = self.load()?;
        let id = items.iter().map(|item| item.id).max().unwrap_or(0) + 1;
        let text: String = text.chars().map(|c| if c == '\t' || c == '\n' || c == '\r' { ' ' } else { c }).collect();
        let item = Item { id, text };
        items.push(item.clone());
        self.save(&items)?;
        Ok(item)
    }

    fn save(&self, items: &[Item]) -> io::Result<()> {
        let text: String = items.iter().map(|item| format!("{}\t{}\n", item.id, item.text)).collect();
        fs::write(&self.path, text)
    }
}
