import { FormEvent, useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  fetchKnowledgeLesson,
  fetchKnowledgeLessons,
  searchKnowledge,
  updateKnowledgeBookmark,
  updateKnowledgeProgress,
} from '@/utils/apiClient';
import {
  GraphArgumentLink,
  KnowledgeLessonDetail,
  KnowledgeLessonSummary,
  KnowledgeSearchResult,
} from '@/types';

const filterKeys = ['tags', 'difficulty', 'media_types'] as const;

type FilterKey = (typeof filterKeys)[number];

type KnowledgeFilters = {
  tags: string[];
  difficulty: string[];
  media_types: string[];
};

export function KnowledgeHub(): JSX.Element {
  const [lessons, setLessons] = useState<KnowledgeLessonSummary[]>([]);
  const [filters, setFilters] = useState<KnowledgeFilters>({ tags: [], difficulty: [], media_types: [] });
  const [selectedLessonId, setSelectedLessonId] = useState<string | null>(null);
  const [lessonDetail, setLessonDetail] = useState<KnowledgeLessonDetail | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResult[]>([]);
  const [selectedFilters, setSelectedFilters] = useState(() => ({
    tags: new Set<string>(),
    difficulty: new Set<string>(),
    media_types: new Set<string>(),
  }));
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchElapsed, setSearchElapsed] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchKnowledgeLessons()
      .then((response) => {
        if (!active) return;
        setLessons(response.lessons);
        setFilters(response.filters);
        if (response.lessons.length && !selectedLessonId) {
          void loadLesson(response.lessons[0].lesson_id);
        }
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : 'Unable to load knowledge lessons.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const loadLesson = async (lessonId: string): Promise<void> => {
    setDetailLoading(true);
    setError(null);
    try {
      const detail = await fetchKnowledgeLesson(lessonId);
      setLessonDetail(detail);
      setSelectedLessonId(lessonId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load lesson.');
    } finally {
      setDetailLoading(false);
    }
  };

  const toggleFilter = (key: FilterKey, value: string): void => {
    setSelectedFilters((prev) => {
      const next = {
        tags: new Set(prev.tags),
        difficulty: new Set(prev.difficulty),
        media_types: new Set(prev.media_types),
      };
      const target = next[key];
      if (target.has(value)) {
        target.delete(value);
      } else {
        target.add(value);
      }
      return next;
    });
  };

  const activeFilterPayload = useMemo(() => {
    const payload: KnowledgeFilters = { tags: [], difficulty: [], media_types: [] };
    filterKeys.forEach((key) => {
      if (selectedFilters[key].size) {
        payload[key] = Array.from(selectedFilters[key]);
      }
    });
    return payload;
  }, [selectedFilters]);

  const handleSearch = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults([]);
      setSearchElapsed(null);
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const response = await searchKnowledge({
        query: searchQuery,
        filters: activeFilterPayload,
      });
      setSearchResults(response.results);
      setSearchElapsed(response.elapsed_ms);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Knowledge search failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleBookmark = async (lessonId: string, bookmarked: boolean): Promise<void> => {
    setError(null);
    try {
      const response = await updateKnowledgeBookmark(lessonId, bookmarked);
      setLessons((prev) =>
        prev.map((lesson) =>
          lesson.lesson_id === lessonId
            ? { ...lesson, bookmarked: response.bookmarked }
            : lesson
        )
      );
      if (lessonDetail && lessonDetail.lesson_id === lessonId) {
        setLessonDetail({ ...lessonDetail, bookmarked: response.bookmarked });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update bookmark.');
    }
  };

  const handleToggleSection = async (sectionId: string, completed: boolean): Promise<void> => {
    if (!lessonDetail) return;
    setError(null);
    try {
      const progress = await updateKnowledgeProgress(lessonDetail.lesson_id, sectionId, completed);
      setLessonDetail({
        ...lessonDetail,
        progress: {
          completed_sections: progress.completed_sections,
          total_sections: progress.total_sections,
          percent_complete: progress.percent_complete,
          last_viewed_at: progress.last_viewed_at ?? lessonDetail.progress.last_viewed_at ?? null,
        },
        sections: lessonDetail.sections.map((section) =>
          section.id === sectionId ? { ...section, completed } : section
        ),
      });
      setLessons((prev) =>
        prev.map((lesson) =>
          lesson.lesson_id === lessonDetail.lesson_id
            ? {
                ...lesson,
                progress: {
                  completed_sections: progress.completed_sections,
                  total_sections: progress.total_sections,
                  percent_complete: progress.percent_complete,
                  last_viewed_at: progress.last_viewed_at ?? lesson.progress.last_viewed_at ?? null,
                },
              }
            : lesson
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update section progress.');
    }
  };

  const activeLesson = lessonDetail;
  const formatNodeLabel = (node: { properties?: Record<string, unknown>; id: string; type: string }): string => {
    if (!node) return 'Unknown node';
    const properties = node.properties ?? {};
    const candidates = ['label', 'title', 'name'];
    for (const key of candidates) {
      const value = properties[key];
      if (typeof value === 'string' && value.trim()) {
        return value.trim();
      }
    }
    return node.id;
  };

  const renderArgumentLinks = (heading: string, links: GraphArgumentLink[]): JSX.Element | null => {
    if (!links.length) return null;
    return (
      <div className="strategy-links">
        <p className="strategy-links-heading">{heading}</p>
        <ul>
          {links.map((link) => (
            <li key={`${link.node.id}:${link.relation}:${link.stance}`}>
              <span className="strategy-node-label">{formatNodeLabel(link.node)}</span>
              <span className="strategy-relation">{link.relation}</span>
              {link.documents.length > 0 && (
                <span className="strategy-documents">Docs: {link.documents.join(', ')}</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="knowledge-hub">
      <header className="knowledge-header">
        <div>
          <h2>Knowledge Hub</h2>
          <p className="knowledge-subtitle">
            Curated legal playbooks with progress tracking and lesson bookmarks.
          </p>
        </div>
        {error && <div role="alert" className="knowledge-error">{error}</div>}
      </header>

      <section className="knowledge-search" aria-label="Search curated resources">
        <form onSubmit={handleSearch} className="knowledge-search-form">
          <label htmlFor="knowledge-query" className="sr-only">
            Search knowledge base
          </label>
          <input
            id="knowledge-query"
            type="search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search for discovery, deposition, privilege guidance..."
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Searching…' : 'Search'}
          </button>
        </form>
        <div className="knowledge-filters" role="group" aria-label="Search filters">
          <fieldset>
            <legend>Tags</legend>
            <div className="filter-grid">
              {filters.tags.map((tag) => (
                <label key={tag}>
                  <input
                    type="checkbox"
                    checked={selectedFilters.tags.has(tag)}
                    onChange={() => toggleFilter('tags', tag)}
                  />
                  {tag}
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>Difficulty</legend>
            <div className="filter-grid">
              {filters.difficulty.map((level) => (
                <label key={level}>
                  <input
                    type="checkbox"
                    checked={selectedFilters.difficulty.has(level)}
                    onChange={() => toggleFilter('difficulty', level)}
                  />
                  {level}
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>Media</legend>
            <div className="filter-grid">
              {filters.media_types.map((media) => (
                <label key={media}>
                  <input
                    type="checkbox"
                    checked={selectedFilters.media_types.has(media)}
                    onChange={() => toggleFilter('media_types', media)}
                  />
                  {media}
                </label>
              ))}
            </div>
          </fieldset>
        </div>
        {searchElapsed !== null && (
          <p className="search-metadata">
            {searchResults.length} result{searchResults.length === 1 ? '' : 's'} in {searchElapsed.toFixed(1)} ms
          </p>
        )}
        {searchResults.length > 0 && (
          <ol className="knowledge-search-results">
            {searchResults.map((result) => (
              <li key={`${result.lesson_id}:${result.section_id}`}>
                <button
                  type="button"
                  onClick={() => {
                    void loadLesson(result.lesson_id);
                    setSearchResults([]);
                  }}
                >
                  <span className="result-title">{result.section_title}</span>
                  <span className="result-lesson">{result.lesson_title}</span>
                  <span className="result-snippet">{result.snippet}</span>
                </button>
              </li>
            ))}
          </ol>
        )}
      </section>

      <div className="knowledge-content">
        <aside className="knowledge-lessons" aria-label="Lesson list">
          {loading && !lessons.length ? (
            <p className="placeholder">Loading curated lessons…</p>
          ) : (
            <ul>
              {lessons.map((lesson) => {
                const percent = Math.round(lesson.progress.percent_complete * 100);
                return (
                  <li key={lesson.lesson_id} data-selected={lesson.lesson_id === selectedLessonId}>
                    <button type="button" onClick={() => void loadLesson(lesson.lesson_id)}>
                      <div className="lesson-header">
                        <h3>{lesson.title}</h3>
                        <span className="lesson-difficulty" data-level={lesson.difficulty}>
                          {lesson.difficulty}
                        </span>
                      </div>
                      <p className="lesson-summary">{lesson.summary}</p>
                      <div className="lesson-meta">
                        <span>{lesson.estimated_minutes} min</span>
                        <span>{percent}% complete</span>
                      </div>
                      <div className="lesson-tags">
                        {lesson.tags.slice(0, 4).map((tag) => (
                          <span key={tag}>{tag}</span>
                        ))}
                      </div>
                    </button>
                    <button
                      type="button"
                      className="bookmark-toggle"
                      aria-pressed={lesson.bookmarked}
                      onClick={() => void handleToggleBookmark(lesson.lesson_id, !lesson.bookmarked)}
                    >
                      {lesson.bookmarked ? '★ Bookmarked' : '☆ Bookmark'}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </aside>
        <section className="knowledge-lesson-view" aria-live="polite">
          {detailLoading && <p className="placeholder">Loading lesson…</p>}
          {!detailLoading && activeLesson && (
            <article>
              <header className="lesson-view-header">
                <div>
                  <h3>{activeLesson.title}</h3>
                  <p>{activeLesson.summary}</p>
                </div>
                <button
                  type="button"
                  onClick={() => void handleToggleBookmark(activeLesson.lesson_id, !activeLesson.bookmarked)}
                  className="bookmark-toggle"
                  aria-pressed={activeLesson.bookmarked}
                >
                  {activeLesson.bookmarked ? '★ Remove bookmark' : '☆ Bookmark lesson'}
                </button>
              </header>
              <div className="lesson-progress-bar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(activeLesson.progress.percent_complete * 100)}>
                <span style={{ width: `${Math.round(activeLesson.progress.percent_complete * 100)}%` }} />
              </div>
              <section className="lesson-meta-block">
                <p>
                  <strong>Estimated time:</strong> {activeLesson.estimated_minutes} minutes
                </p>
                <p>
                  <strong>Jurisdictions:</strong> {activeLesson.jurisdictions.join(', ') || 'General'}
                </p>
                {activeLesson.media.length > 0 && (
                  <ul className="lesson-media" aria-label="Related media">
                    {activeLesson.media.map((item) => (
                      <li key={`${item.type}:${item.url}`}>
                        <a href={item.url} target="_blank" rel="noreferrer">
                          {item.title}
                        </a>{' '}
                        <span className="media-meta">{item.provider ?? item.type}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              {activeLesson.strategy_brief && (
                <section className="lesson-strategy-map" aria-label="Strategy map briefing">
                  <h4>Strategy Map</h4>
                  <p className="strategy-summary">{activeLesson.strategy_brief.summary}</p>
                  {activeLesson.strategy_brief.focus_nodes.length > 0 && (
                    <div className="strategy-focus">
                      <h5>Focus Nodes</h5>
                      <ul>
                        {activeLesson.strategy_brief.focus_nodes.map((node) => (
                          <li key={node.id}>
                            <span className="strategy-node-label">{formatNodeLabel(node)}</span>
                            <span className="strategy-node-type">{node.type}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {activeLesson.strategy_brief.argument_map.length > 0 && (
                    <div className="strategy-arguments">
                      <h5>Argument Map</h5>
                      {activeLesson.strategy_brief.argument_map.map((entry) => (
                        <div key={entry.node.id} className="strategy-argument">
                          <h6>{formatNodeLabel(entry.node)}</h6>
                          {renderArgumentLinks('Supporting', entry.supporting)}
                          {renderArgumentLinks('Opposing', entry.opposing)}
                          {renderArgumentLinks('Neutral', entry.neutral)}
                        </div>
                      ))}
                    </div>
                  )}
                  {activeLesson.strategy_brief.contradictions.length > 0 && (
                    <div className="strategy-contradictions">
                      <h5>Contradictions</h5>
                      <ul>
                        {activeLesson.strategy_brief.contradictions.map((item, index) => (
                          <li key={`${item.source.id}:${item.target.id}:${index}`}>
                            <span className="strategy-node-label">{formatNodeLabel(item.source)}</span>
                            <span className="strategy-relation">{item.relation}</span>
                            <span className="strategy-node-label">{formatNodeLabel(item.target)}</span>
                            {item.documents.length > 0 && (
                              <span className="strategy-documents">Docs: {item.documents.join(', ')}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {activeLesson.strategy_brief.leverage_points.length > 0 && (
                    <div className="strategy-leverage">
                      <h5>Leverage Points</h5>
                      <ul>
                        {activeLesson.strategy_brief.leverage_points.map((point) => (
                          <li key={point.node.id}>
                            <span className="strategy-node-label">{formatNodeLabel(point.node)}</span>
                            <span className="strategy-reason">{point.reason}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </section>
              )}
              <div className="lesson-sections">
                {activeLesson.sections.map((section) => (
                  <details key={section.id} open>
                    <summary>
                      <span>{section.title}</span>
                      <button
                        type="button"
                        onClick={() => void handleToggleSection(section.id, !section.completed)}
                        className="section-toggle"
                      >
                        {section.completed ? 'Mark as incomplete' : 'Mark complete'}
                      </button>
                    </summary>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.content}</ReactMarkdown>
                  </details>
                ))}
              </div>
            </article>
          )}
          {!detailLoading && !activeLesson && !loading && (
            <p className="placeholder">Select a lesson to begin.</p>
          )}
        </section>
      </div>
    </div>
  );
}
