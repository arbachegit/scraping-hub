/**
 * GitHub API Service
 * Perfil técnico de desenvolvedores - repositórios, linguagens, contribuições
 */

import logger from '../utils/logger.js';

const GITHUB_BASE_URL = 'https://api.github.com';
const GITHUB_TOKEN = process.env.GITHUB_TOKEN; // Optional, increases rate limit

/**
 * Make request to GitHub API
 * @param {string} endpoint - API endpoint
 * @returns {Promise<Object|null>} API response or null
 */
async function githubRequest(endpoint) {
  const headers = {
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'iconsai-scraping'
  };

  if (GITHUB_TOKEN) {
    headers['Authorization'] = `Bearer ${GITHUB_TOKEN}`;
  }

  try {
    const response = await fetch(`${GITHUB_BASE_URL}${endpoint}`, { headers });

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      logger.warn('GitHub API error', { status: response.status, endpoint });
      return null;
    }

    return response.json();
  } catch (error) {
    logger.error('GitHub request error', { error: error.message, endpoint });
    return null;
  }
}

/**
 * Search for GitHub user by name
 * @param {string} name - Person name
 * @param {string} location - Optional location filter (e.g., "Brazil")
 * @returns {Promise<Array>} List of matching GitHub users
 */
export async function searchUserByName(name, location = null) {
  let query = name.replace(/\s+/g, '+');
  if (location) {
    query += `+location:${encodeURIComponent(location)}`;
  }

  const data = await githubRequest(`/search/users?q=${query}&per_page=5`);

  if (!data || !data.items) {
    return [];
  }

  // Enrich each user with profile details
  const enrichedUsers = [];
  for (const user of data.items.slice(0, 3)) {
    const profile = await getUserProfile(user.login);
    if (profile) {
      enrichedUsers.push(profile);
    }
  }

  return enrichedUsers;
}

/**
 * Get detailed GitHub user profile
 * @param {string} username - GitHub username
 * @returns {Promise<Object|null>} User profile with stats
 */
export async function getUserProfile(username) {
  const user = await githubRequest(`/users/${username}`);

  if (!user) {
    return null;
  }

  // Get user's repositories
  const repos = await githubRequest(`/users/${username}/repos?sort=updated&per_page=100`);

  // Calculate language stats
  const languageStats = {};
  let totalStars = 0;
  let totalForks = 0;

  if (repos && Array.isArray(repos)) {
    for (const repo of repos) {
      if (repo.language) {
        languageStats[repo.language] = (languageStats[repo.language] || 0) + 1;
      }
      totalStars += repo.stargazers_count || 0;
      totalForks += repo.forks_count || 0;
    }
  }

  // Sort languages by count
  const topLanguages = Object.entries(languageStats)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([lang, count]) => ({ language: lang, repos: count }));

  return {
    username: user.login,
    name: user.name,
    bio: user.bio,
    company: user.company,
    location: user.location,
    email: user.email,
    blog: user.blog,
    twitter_username: user.twitter_username,
    avatar_url: user.avatar_url,
    html_url: user.html_url,
    public_repos: user.public_repos,
    followers: user.followers,
    following: user.following,
    created_at: user.created_at,
    // Calculated stats
    total_stars: totalStars,
    total_forks: totalForks,
    top_languages: topLanguages,
    hireable: user.hireable
  };
}

/**
 * Get GitHub profile by username (direct lookup)
 * @param {string} username - GitHub username
 * @returns {Promise<Object|null>} User profile
 */
export async function getProfileByUsername(username) {
  return getUserProfile(username);
}

/**
 * Analyze technical competencies from GitHub profile
 * @param {Object} profile - GitHub profile object
 * @returns {Object} Competencies analysis
 */
export function analyzeCompetencies(profile) {
  if (!profile) {
    return null;
  }

  const competencies = {
    nivel_tecnico: 'junior', // junior, pleno, senior, expert
    linguagens: profile.top_languages?.map(l => l.language) || [],
    score_atividade: 0,
    score_influencia: 0,
    anos_experiencia: 0
  };

  // Calculate experience based on account age
  if (profile.created_at) {
    const created = new Date(profile.created_at);
    const now = new Date();
    competencies.anos_experiencia = Math.floor((now - created) / (365.25 * 24 * 60 * 60 * 1000));
  }

  // Calculate activity score (0-100)
  const repoScore = Math.min(profile.public_repos * 2, 40);
  const starScore = Math.min(profile.total_stars * 0.5, 30);
  const languageScore = Math.min(profile.top_languages?.length * 5, 20);
  competencies.score_atividade = Math.round(repoScore + starScore + languageScore);

  // Calculate influence score (0-100)
  const followerScore = Math.min(profile.followers * 0.2, 50);
  const forkScore = Math.min(profile.total_forks * 2, 30);
  competencies.score_influencia = Math.round(followerScore + forkScore);

  // Determine level
  const totalScore = competencies.score_atividade + competencies.score_influencia;
  if (totalScore >= 150 && competencies.anos_experiencia >= 8) {
    competencies.nivel_tecnico = 'expert';
  } else if (totalScore >= 100 && competencies.anos_experiencia >= 5) {
    competencies.nivel_tecnico = 'senior';
  } else if (totalScore >= 50 && competencies.anos_experiencia >= 2) {
    competencies.nivel_tecnico = 'pleno';
  }

  return competencies;
}

/**
 * Search and analyze person's GitHub presence
 * @param {string} name - Person name
 * @param {string} company - Company name (optional, for better matching)
 * @returns {Promise<Object>} GitHub enrichment result
 */
export async function enrichPersonGitHub(name, company = null) {
  const result = {
    found: false,
    profiles: [],
    best_match: null,
    competencies: null
  };

  // Search by name
  const users = await searchUserByName(name, 'Brazil');

  if (!users.length) {
    return result;
  }

  result.profiles = users;
  result.found = true;

  // Try to find best match based on company
  if (company) {
    const companyLower = company.toLowerCase();
    const match = users.find(u =>
      u.company?.toLowerCase().includes(companyLower) ||
      u.bio?.toLowerCase().includes(companyLower)
    );
    if (match) {
      result.best_match = match;
    }
  }

  // Use first result as best match if not found by company
  if (!result.best_match && users.length > 0) {
    result.best_match = users[0];
  }

  // Analyze competencies of best match
  if (result.best_match) {
    result.competencies = analyzeCompetencies(result.best_match);
  }

  return result;
}
