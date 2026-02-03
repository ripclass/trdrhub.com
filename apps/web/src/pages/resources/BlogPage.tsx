import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { Calendar, User, ArrowRight, Tag } from "lucide-react";

const featuredPost = {
  title: "The End of Paper: How Digital LCs are Finally Happening",
  excerpt: "After decades of false starts, the adoption of MLETR and digital trade standards is reaching a tipping point. Here's what it means for your business.",
  author: "Sarah Chen",
  date: "Jan 15, 2026",
  category: "Industry Trends",
  image: "https://images.unsplash.com/photo-1611974765270-ca12586343bb?q=80&w=2070&auto=format&fit=crop"
};

const posts = [
  {
    title: "5 Common Discrepancies in Bills of Lading (and How to Fix Them)",
    excerpt: "A deep dive into Article 20 of UCP 600 and the most frequent errors we see in transport documents.",
    author: "Mike Ross",
    date: "Jan 10, 2026",
    category: "Compliance",
    readTime: "5 min read"
  },
  {
    title: "Understanding Sanctions Screening for Dual-Use Goods",
    excerpt: "Navigating the complex landscape of export controls and ensuring your goods aren't flagged.",
    author: "Elena Rodriguez",
    date: "Jan 05, 2026",
    category: "Risk Management",
    readTime: "8 min read"
  },
  {
    title: "API-First Trade Finance: Integrating Validation into Your ERP",
    excerpt: "A technical guide for developers looking to automate document checks within SAP or Oracle.",
    author: "David Kim",
    date: "Dec 28, 2025",
    category: "Engineering",
    readTime: "12 min read"
  }
];

const BlogPage = () => {
  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="pt-32 md:pt-48 pb-24 relative min-h-screen">
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none fixed" />

        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          
          <div className="text-center mb-16">
            <h1 className="text-4xl md:text-6xl font-bold text-white mb-6 font-display">
              Trade Insights
            </h1>
            <p className="text-lg text-[#EDF5F2]/60 max-w-2xl mx-auto font-light">
              Expert analysis, technical guides, and industry updates from the TRDR Hub team.
            </p>
          </div>

          {/* Featured Post */}
          <div className="max-w-6xl mx-auto mb-20">
            <Link to="#" className="group relative block rounded-3xl overflow-hidden aspect-[21/9] border border-[#EDF5F2]/10">
              <img 
                src={featuredPost.image} 
                alt={featuredPost.title}
                className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#00261C] via-[#00261C]/50 to-transparent" />
              
              <div className="absolute bottom-0 left-0 p-8 md:p-12 max-w-3xl">
                <div className="flex items-center gap-4 mb-4 text-sm font-mono">
                  <span className="bg-[#B2F273] text-[#00261C] px-3 py-1 rounded-full font-bold uppercase tracking-wider">
                    {featuredPost.category}
                  </span>
                  <span className="text-[#EDF5F2]/80 flex items-center gap-2">
                    <Calendar className="w-4 h-4" /> {featuredPost.date}
                  </span>
                </div>
                <h2 className="text-3xl md:text-5xl font-bold text-white mb-4 font-display leading-tight group-hover:text-[#B2F273] transition-colors">
                  {featuredPost.title}
                </h2>
                <p className="text-lg text-[#EDF5F2]/80 line-clamp-2 mb-6">
                  {featuredPost.excerpt}
                </p>
                <div className="flex items-center gap-2 text-[#B2F273] font-bold">
                  Read Article <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            </Link>
          </div>

          {/* Recent Posts Grid */}
          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {posts.map((post, index) => (
              <Link 
                key={index}
                to="#"
                className="group bg-[#00382E]/30 border border-[#EDF5F2]/10 rounded-2xl p-8 hover:border-[#B2F273]/30 transition-all hover:-translate-y-1"
              >
                <div className="flex items-center justify-between mb-6">
                  <span className="text-[#B2F273] font-mono text-xs uppercase tracking-wider">
                    {post.category}
                  </span>
                  <span className="text-[#EDF5F2]/40 text-xs font-mono">
                    {post.readTime}
                  </span>
                </div>
                <h3 className="text-xl font-bold text-white mb-3 font-display group-hover:text-[#B2F273] transition-colors">
                  {post.title}
                </h3>
                <p className="text-[#EDF5F2]/60 text-sm leading-relaxed mb-6">
                  {post.excerpt}
                </p>
                <div className="flex items-center gap-3 pt-6 border-t border-[#EDF5F2]/5">
                  <div className="w-8 h-8 rounded-full bg-[#00261C] flex items-center justify-center border border-[#EDF5F2]/10">
                    <User className="w-4 h-4 text-[#EDF5F2]/60" />
                  </div>
                  <div className="text-xs">
                    <div className="text-white font-medium">{post.author}</div>
                    <div className="text-[#EDF5F2]/40">{post.date}</div>
                  </div>
                </div>
              </Link>
            ))}
          </div>

        </div>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default BlogPage;
